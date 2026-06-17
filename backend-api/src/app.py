"""
app.py — Main FastAPI application with /predict endpoint, admin endpoints,
database logging, CORS middleware, and static file serving for admin dashboard.
"""
import sys
import os
import time
import threading
import subprocess
import secrets
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import joblib
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import config
from preprocessing import clean_text
from feature_extractor import extract_7_features
from embedding_extractor import embeddings_for
from database import (
    init_db,
    log_prediction,
    get_predictions,
    get_stats,
    log_model,
    get_models,
    get_latest_model,
    log_activity,
    get_activity_log,
    verify_user,
)


# ── Request / Response Models ────────────────────────────────────────────

class PredictRequest(BaseModel):
    text: str

class LoginRequest(BaseModel):
    username: str
    password: str

# ── App Setup ────────────────────────────────────────────────────────────

app = FastAPI(title="Taglish Disinformation Detector API")

# CORS — allow Chrome extension and admin dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin frontend serving moved to bottom to prevent routing collisions

# ── Admin Authentication ─────────────────────────────────────────────────

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# In-memory session store: token -> {"username": str, "expires": float}
active_sessions = {}
SESSION_EXPIRY = 8 * 3600  # 8 hours

def get_current_admin(request: Request) -> str:
    """Dependency to check admin auth via Bearer token or cookie."""
    token = request.cookies.get("admin_token")
    auth_header = request.headers.get("Authorization")
    
    if not token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
    if not token or token not in active_sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
        
    session = active_sessions[token]
    if time.time() > session["expires"]:
        del active_sessions[token]
        raise HTTPException(status_code=401, detail="Session expired")
        
    return session["username"]


@app.post("/admin-api/login")
def admin_login(req: LoginRequest, request: Request, response: Response):
    client_ip = request.client.host if request.client else "unknown"
    
    # Strip whitespace to prevent accidental login failures
    username = req.username.strip()
    password = req.password.strip()

    # 1. EMERGENCY OVERRIDE: Always allow built-in admin to prevent lockout
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        user = {"username": ADMIN_USERNAME, "role": "admin"}
        try:
            log_activity("ADMIN_LOGIN_OVERRIDE", f"Emergency override used for {username}", performed_by=username, ip_address=client_ip)
        except Exception:
            print(f"[app] Emergency override login used for {username}")
    else:
        # 2. Try database lookup
        user = None
        try:
            user = verify_user(username, password)
        except Exception:
            # DB errors should not permanently lock out
            user = None

    if user:
        token = secrets.token_hex(32)
        active_sessions[token] = {
            "username": user["username"],
            "role": user.get("role", "admin"),
            "expires": time.time() + SESSION_EXPIRY
        }
        # Set cookie for safety
        response.set_cookie(key="admin_token", value=token, httponly=True, max_age=SESSION_EXPIRY)
        log_activity("ADMIN_LOGIN", f"User {user['username']} logged in", performed_by=user['username'], ip_address=client_ip)
        return {"status": "success", "token": token, "username": user["username"]}

    log_activity("ADMIN_LOGIN_FAILED", f"Invalid login attempt for username: {req.username}", performed_by="unknown", ip_address=client_ip)
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/admin-api/logout")
def admin_logout(request: Request, response: Response):
    token = request.cookies.get("admin_token")
    auth_header = request.headers.get("Authorization")
    if not token and auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
    if token in active_sessions:
        username = active_sessions[token]["username"]
        del active_sessions[token]
        log_activity("ADMIN_LOGOUT", "Admin logged out", performed_by=username)
        
    response.delete_cookie("admin_token")
    return {"status": "logged out"}


@app.get("/admin-api/check-auth")
def check_auth(username: str = Depends(get_current_admin)):
    return {"authenticated": True, "username": username}


# ── Model Loading & Startup ──────────────────────────────────────────────

MODEL = None
META = None

def load_model_bundle():
    """Load the model bundle from disk."""
    global MODEL, META
    hybrid_path = os.path.join(config.BASE_DIR, "models", "logistic_regression.joblib")
    embed_path = os.path.join(config.BASE_DIR, "models", "distilbert_only_lr.joblib")
    
    if os.path.exists(hybrid_path):
        MODEL = joblib.load(hybrid_path)
        META = {"best": "hybrid"}
        print(f"[app] Loaded hybrid model from {hybrid_path}")
    elif os.path.exists(embed_path):
        MODEL = joblib.load(embed_path)
        META = {"best": "embed"}
        print(f"[app] Loaded embed model from {embed_path}")
    elif os.path.exists(config.MODEL_PATH):
        bundle = joblib.load(config.MODEL_PATH)
        if isinstance(bundle, dict):
            MODEL = bundle.get("model")
            META = bundle.get("meta", {})
        else:
            MODEL = bundle
            META = {"best": "hybrid"}
        print(f"[app] Loaded model from {config.MODEL_PATH}")
    else:
        print("[app] WARNING: No model file found!")

@app.on_event("startup")
def startup_event():
    init_db()
    load_model_bundle()
    # Warm up DistilBERT — runs one dummy inference so the first real
    # request is as fast as subsequent ones (no cold-start JIT delay).
    try:
        from embedding_extractor import embeddings_for
        embeddings_for(["warmup"])
        print("[app] DistilBERT warm-up complete.")
    except Exception as e:
        print(f"[app] Warm-up skipped: {e}")
    log_activity("SYSTEM_START", "FastAPI server started successfully")


# ── Explanation Generator ─────────────────────────────────────────────────

def generate_explanation(label: str, features: dict, confidence: float) -> dict:
    """
    Produces a plain-language explanation and per-feature flags indicating
    which features were elevated and contributed to the classification.
    """
    is_dis = label == "Disinformation"
    flags = {}

    # Thresholds — tune these to match your dataset norms
    flags["code_switching_ratio"]   = features["code_switching_ratio"]   > 0.15
    flags["urgency_count"]          = features["urgency_count"]          >= 2
    flags["particle_count"]         = features["particle_count"]         >= 3
    flags["punctuation_intensity"]  = features["punctuation_intensity"]  > 0.05
    flags["caps_ratio"]             = features["caps_ratio"]             > 0.20
    flags["repeated_chars"]         = features["repeated_chars"]         >= 1
    flags["emotional_count"]        = features["emotional_count"]        >= 2

    triggered = [k for k, v in flags.items() if v]

    feature_labels = {
        "code_switching_ratio":  "heavy Taglish code-switching",
        "urgency_count":         "urgency cues (e.g. 'agad!', 'PAKI-SHARE')",
        "particle_count":        "many Filipino filler particles",
        "punctuation_intensity": "high punctuation intensity",
        "caps_ratio":            "excessive capitalization",
        "repeated_chars":        "repeated/stretched characters (e.g. 'graaabe')",
        "emotional_count":       "emotionally charged vocabulary",
    }

    if is_dis:
        if triggered:
            readable = [feature_labels[k] for k in triggered]
            if len(readable) == 1:
                joined = readable[0]
            elif len(readable) == 2:
                joined = f"{readable[0]} and {readable[1]}"
            else:
                joined = ", ".join(readable[:-1]) + f", and {readable[-1]}"
            summary = (
                f"This post was flagged as DISINFORMATION with "
                f"{confidence*100:.1f}% confidence. The AI detected {joined} — "
                f"patterns commonly found in misleading or manipulative Taglish content."
            )
        else:
            summary = (
                f"This post was flagged as DISINFORMATION with "
                f"{confidence*100:.1f}% confidence based on the overall semantic "
                f"context analyzed by the DistilBERT language model."
            )
    else:
        if not triggered:
            summary = (
                f"This post was classified as NON-DISINFORMATION with "
                f"{confidence*100:.1f}% confidence. No strong linguistic red flags "
                f"were detected — the language appears balanced and factual."
            )
        else:
            readable = [feature_labels[k] for k in triggered]
            joined = ", ".join(readable) if len(readable) > 1 else readable[0]
            summary = (
                f"This post was classified as NON-DISINFORMATION with "
                f"{confidence*100:.1f}% confidence. While {joined} "
                f"{'were' if len(triggered) > 1 else 'was'} detected, the overall "
                f"semantic context did not indicate disinformation."
            )

    return {"summary": summary, "feature_flags": flags, "triggered_features": triggered}


# ── Public Endpoints ─────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "model": "hybrid-distilbert-lr" if META and META.get("best") == "hybrid" else "distilbert-only"}


@app.post("/predict")
def predict(req: PredictRequest, request: Request) -> Dict[str, Any]:
    text = req.text
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    if MODEL is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    clean = clean_text(text)
    feats = extract_7_features(clean)

    # Measure inference time
    t0 = time.perf_counter()
    emb = embeddings_for([clean])

    if META and META.get("best") == "embed":
        vector = emb[0]
    else:
        vector = np.hstack([emb[0], feats])

    try:
        proba = None
        if hasattr(MODEL, "predict_proba"):
            proba = MODEL.predict_proba(vector.reshape(1, -1))[0]
            confidence = float(max(proba))
        else:
            confidence = 1.0

        pred = int(MODEL.predict(vector.reshape(1, -1))[0])
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))

    t1 = time.perf_counter()
    inference_ms = round((t1 - t0) * 1000, 2)

    # Map label
    label = "Disinformation" if pred == 1 else "Non-Disinformation"

    # Build features dict
    features = {
        "code_switching_ratio": round(float(feats[0]), 4),
        "urgency_count": int(feats[6]),
        "particle_count": int(feats[1]),
        "punctuation_intensity": round(float(feats[2]), 4),
        "caps_ratio": round(float(feats[3]), 4),
        "repeated_chars": int(feats[4]),
        "emotional_count": int(feats[5]),
    }

    # Log to database
    try:
        log_prediction(
            input_text=text,
            label=label,
            label_code=pred,
            confidence=round(confidence, 4),
            inference_ms=inference_ms,
            code_switching_ratio=features["code_switching_ratio"],
            urgency_count=features["urgency_count"],
            particle_count=features["particle_count"],
            punctuation_intensity=features["punctuation_intensity"],
            caps_ratio=features["caps_ratio"],
            repeated_chars=features["repeated_chars"],
            emotional_count=features["emotional_count"],
        )
        log_activity(
            action="PREDICTION",
            description=f"Label: {label}, Confidence: {confidence:.2f}",
            performed_by="end_user",
            ip_address=request.client.host if request.client else "unknown"
        )
    except Exception as e:
        print(f"[app] DB logging failed (non-fatal): {e}")

    explanation = generate_explanation(label, features, confidence)

    return {
        "label": label,
        "label_code": pred,
        "confidence": round(confidence, 4),
        "inference_ms": inference_ms,
        "features": features,
        "explanation": explanation["summary"],
        "feature_flags": explanation["feature_flags"],
        "triggered_features": explanation["triggered_features"],
    }


# ── Protected Admin Endpoints ────────────────────────────────────────────

@app.get("/admin-api/stats")
def admin_stats(username: str = Depends(get_current_admin)):
    _ = username  # Silence unused variable warning
    return {"stats": get_stats()}

@app.get("/admin-api/predictions")
def admin_predictions(limit: int = 200, username: str = Depends(get_current_admin)):
    _ = username
    return {"predictions": get_predictions(limit=limit)}

@app.get("/admin-api/models")
def admin_models(username: str = Depends(get_current_admin)):
    _ = username
    return {"models": get_models()}

@app.get("/admin-api/models/latest")
def admin_latest_model(username: str = Depends(get_current_admin)):
    _ = username
    model = get_latest_model()
    if not model:
        return {"error": "No models found"}
    return {"model": model}

@app.get("/admin-api/activity-log")
def admin_activity_log(limit: int = 100, username: str = Depends(get_current_admin)):
    _ = username
    return {"activity_log": get_activity_log(limit=limit)}

# ── Retrain Endpoint ─────────────────────────────────────────────────────

retrain_status = {"running": False, "message": "Idle"}

@app.get("/admin-api/retrain/status")
def admin_retrain_status(username: str = Depends(get_current_admin)):
    return retrain_status

@app.post("/admin-api/retrain")
def admin_retrain(username: str = Depends(get_current_admin)):
    global retrain_status
    if retrain_status["running"]:
        raise HTTPException(status_code=409, detail="Retraining already in progress")

    retrain_status = {"running": True, "message": "Starting retraining..."}
    log_activity("RETRAIN_STARTED", "Model retraining initiated", performed_by=username)

    def run_training():
        global retrain_status, MODEL, META
        try:
            retrain_status["message"] = "Running train_model.py..."
            train_script = os.path.join(config.BASE_DIR, "src", "train_model.py")
            
            # Use same venv for the subprocess
            python_exe = sys.executable
            
            result = subprocess.run(
                [python_exe, train_script],
                cwd=config.BASE_DIR,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 minute timeout
            )
            
            if result.returncode == 0:
                retrain_status["message"] = "Retraining completed successfully"
                retrain_status["running"] = False
                load_model_bundle()
                log_activity("RETRAIN_COMPLETED", "Model retraining completed successfully", performed_by=username)
            else:
                retrain_status["message"] = f"Retraining failed: {result.stderr[:200]}"
                retrain_status["running"] = False
                log_activity("RETRAIN_FAILED", f"Retraining failed: {result.stderr}", performed_by=username)
        except subprocess.TimeoutExpired:
            retrain_status["message"] = "Retraining timeout (30 min limit)"
            retrain_status["running"] = False
            log_activity("RETRAIN_TIMEOUT", "Model retraining timed out", performed_by=username)
        except Exception as e:
            retrain_status["message"] = str(e)
            retrain_status["running"] = False
            log_activity("RETRAIN_ERROR", f"Retraining error: {str(e)}", performed_by=username)

    thread = threading.Thread(target=run_training, daemon=True)
    thread.start()
    
    return {"status": "retrain_started", "message": retrain_status["message"]}


# ── Dataset Upload Endpoint ──────────────────────────────────────────────────

UPLOAD_DIR = os.path.join(config.BASE_DIR, "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Track the most recently uploaded dataset path
uploaded_dataset_path: Optional[str] = None

from fastapi import UploadFile, File

@app.post("/admin-api/upload-dataset")
async def upload_dataset(
    file: UploadFile = File(...),
    username: str = Depends(get_current_admin)
):
    global uploaded_dataset_path

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted.")

    # Save with timestamp to avoid overwriting
    import time as _time
    safe_name = f"uploaded_{int(_time.time())}_{file.filename}"
    dest = os.path.join(UPLOAD_DIR, safe_name)

    contents = await file.read()
    with open(dest, "wb") as f:
        f.write(contents)

    uploaded_dataset_path = dest
    log_activity("DATASET_UPLOADED", f"Dataset uploaded: {safe_name}", performed_by=username)
    return {"status": "ok", "filename": safe_name, "path": dest, "size_bytes": len(contents)}


@app.get("/admin-api/upload-dataset/status")
def upload_status(username: str = Depends(get_current_admin)):
    _ = username
    if uploaded_dataset_path and os.path.exists(uploaded_dataset_path):
        return {
            "has_upload": True,
            "filename": os.path.basename(uploaded_dataset_path),
            "size_bytes": os.path.getsize(uploaded_dataset_path),
        }
    return {"has_upload": False, "filename": None}


# ── Retrain with Uploaded Dataset ───────────────────────────────────────────

@app.post("/admin-api/retrain-uploaded")
def admin_retrain_uploaded(username: str = Depends(get_current_admin)):
    global retrain_status, uploaded_dataset_path

    if retrain_status["running"]:
        raise HTTPException(status_code=409, detail="Retraining already in progress.")

    if not uploaded_dataset_path or not os.path.exists(uploaded_dataset_path):
        raise HTTPException(status_code=400, detail="No uploaded dataset found. Please upload a CSV first.")

    dataset_to_use = uploaded_dataset_path
    retrain_status = {"running": True, "message": f"Starting retrain with uploaded dataset: {os.path.basename(dataset_to_use)}"}
    log_activity("RETRAIN_UPLOAD_STARTED", f"Retrain with uploaded dataset: {os.path.basename(dataset_to_use)}", performed_by=username)

    def run_training_uploaded():
        global retrain_status, MODEL, META
        try:
            retrain_status["message"] = f"Training with: {os.path.basename(dataset_to_use)}..."
            train_script = os.path.join(config.BASE_DIR, "src", "train_model.py")
            python_exe = sys.executable

            env = os.environ.copy()
            env["TAGLISH_DATASET_OVERRIDE"] = dataset_to_use  # train_model.py reads this

            result = subprocess.run(
                [python_exe, train_script],
                cwd=config.BASE_DIR,
                capture_output=True,
                text=True,
                timeout=1800,
                env=env,
            )

            if result.returncode == 0:
                retrain_status["message"] = "Retrain with uploaded dataset complete. Reloading model..."
                load_model_bundle()
                retrain_status["message"] = "Retraining complete. Model updated and reloaded."
                log_activity("RETRAIN_UPLOAD_COMPLETE", "Retrain with uploaded dataset completed", performed_by="system")
            else:
                retrain_status["message"] = f"Training failed: {result.stderr[-500:]}"
                log_activity("RETRAIN_UPLOAD_FAILED", f"Retrain failed: {result.stderr[-200:]}", performed_by="system")
        except subprocess.TimeoutExpired:
            retrain_status["message"] = "Error: Training timed out after 30 minutes."
            log_activity("RETRAIN_UPLOAD_FAILED", "Retrain timed out", performed_by="system")
        except Exception as e:
            retrain_status["message"] = f"Error: {str(e)}"
            log_activity("RETRAIN_UPLOAD_FAILED", f"Error: {str(e)}", performed_by="system")
        finally:
            retrain_status["running"] = False

    thread = threading.Thread(target=run_training_uploaded, daemon=True)
    thread.start()
    return {"status": "started", "message": retrain_status["message"]}


# ── Static Files / SPA Mounting ──────────────────────────────────────────
# Future production builds can be served here if needed.
