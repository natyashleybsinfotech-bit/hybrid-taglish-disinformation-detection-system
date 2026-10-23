"""FastAPI application for the SuriPH content screening service."""

from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import io
import json
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

import config
request_logger = logging.getLogger("suriph.requests")
if not request_logger.handlers:
    request_logger.addHandler(logging.StreamHandler())
request_logger.setLevel(logging.INFO)
request_logger.propagate = False
try:
    from . import database
    from .feature_display import describe
    from .fact_check import search_fact_checks
    from .media_processing import MediaProcessingError, extract_image_text, process_video, service_health
    from .model_runtime import (
        ModelUnavailableError, classify, initialize_model, model_health, normalize_text,
    )
    from .retrieval import retrieve_related_sources
    from .topic_classifier import suggest_topic
    from .traffic_limits import TrafficLimits
except ImportError:  # Supports the legacy test runner that adds src/ to sys.path.
    import database
    from feature_display import describe
    from fact_check import search_fact_checks
    from media_processing import MediaProcessingError, extract_image_text, process_video, service_health
    from model_runtime import (
        ModelUnavailableError, classify, initialize_model, model_health, normalize_text,
    )
    from retrieval import retrieve_related_sources
    from topic_classifier import suggest_topic
    from traffic_limits import TrafficLimits


class ScreenRequest(BaseModel):
    text: str = Field(min_length=1, max_length=config.MAX_TEXT_CHARACTERS)
    page_url: str | None = Field(default=None, max_length=4_000)
    page_title: str | None = Field(default=None, max_length=500)
    context: dict[str, Any] | None = None
    retrieve_sources: bool = False


class CandidateRequest(ScreenRequest):
    consent_to_store: Literal[True]


class SourceLookupRequest(BaseModel):
    text: str = Field(min_length=1, max_length=config.MAX_TEXT_CHARACTERS)
    page_url: str | None = Field(default=None, max_length=4_000)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=500)


class CandidateReviewRequest(BaseModel):
    decision: Literal["approve", "revise", "exclude"]
    proposed_label: Literal["Misleading", "Non-Misleading"] | None = None
    notes: str | None = Field(default=None, max_length=4_000)
    language: Literal["Taglish", "Filipino", "English"] | None = None
    topic: str | None = Field(default=None, max_length=120)
    claim_group_id: str | None = Field(default=None, max_length=120)


class EvidenceRequest(BaseModel):
    source_url: str = Field(min_length=8, max_length=4_000)
    publisher: str | None = Field(default=None, max_length=200)
    rating: str | None = Field(default=None, max_length=120)
    claim_match_status: Literal["unreviewed", "matched", "not_matched"] = "unreviewed"
    notes: str | None = Field(default=None, max_length=4_000)


class IndependentAnnotationRequest(BaseModel):
    proposed_label: Literal["Misleading", "Non-Misleading"]
    annotation_round: str = Field(default="pilot", min_length=1, max_length=40)
    evidence_sufficient: bool
    notes: str | None = Field(default=None, max_length=4_000)


class DatasetVersionRequest(BaseModel):
    version_name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=4_000)


class DatasetItemRequest(BaseModel):
    candidate_sample_id: int
    final_label: Literal["Misleading", "Non-Misleading"]
    partition_name: Literal["train", "validation", "test"]
    claim_group_id: str = Field(min_length=1, max_length=120)


class ModelVersionRequest(BaseModel):
    dataset_version_id: int
    model_name: str = Field(min_length=1, max_length=160)
    version_name: str = Field(min_length=1, max_length=120)
    feature_mode: Literal["hybrid_distilbert", "distilbert", "linguistic", "tfidf"]
    metrics: dict[str, Any]
    artifact_path: str = Field(min_length=1, max_length=2_000)


class ModelReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]


class RetrainingRequest(BaseModel):
    dataset_version_id: int
    requested_version_name: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    config.validate_runtime_config()
    migration = database.migrate() if config.AUTO_MIGRATE else database.database_health()
    if migration["status"] != "available" and config.APP_ENV == "production":
        raise RuntimeError("Database migration failed; refusing production startup.")
    if migration["status"] == "available":
        try:
            created = database.ensure_bootstrap_admin()
            if created:
                database.log_audit("ADMIN_BOOTSTRAPPED", "Initial administrator created.")
            viewer_created = database.ensure_bootstrap_viewer()
            if viewer_created:
                database.log_audit("VIEWER_BOOTSTRAPPED", "Initial AFP view-only account created.")
        except Exception:
            if config.APP_ENV == "production":
                raise
            logging.exception("Database/bootstrap initialization failed")
    state = await run_in_threadpool(initialize_model)
    if not state["ready"]:
        logging.error("%s", state["error"])
    # Keep health/readiness reachable after a model failure. Prediction fails 503.
    yield


app = FastAPI(title="SuriPH API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(config.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(config.TRUSTED_HOSTS))
app.add_middleware(TrafficLimits, enabled=config.TRAFFIC_LIMITS_ENABLED or config.APP_ENV == "production")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    started = time.perf_counter()
    if request.method == "POST" and request.url.path.startswith("/admin-api/"):
        origin = request.headers.get("origin")
        if origin and origin not in config.CORS_ORIGINS:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Origin is not allowed."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    request_logger.info(json.dumps({"event": "request", "request_id": uuid.uuid4().hex, "method": request.method,
                            "route": request.scope.get("route").path if request.scope.get("route") else "unmatched",
                            "status": response.status_code, "duration_ms": round((time.perf_counter() - started) * 1000, 2)}))
    return response


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derived_recency(published_at: Any) -> str:
    if not isinstance(published_at, str) or not published_at.strip():
        return "Could not determine"
    try:
        parsed = datetime.fromisoformat(published_at.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return "Could not determine"
        elapsed = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
        if elapsed.total_seconds() < 0:
            return "Could not determine"
        minutes = int(elapsed.total_seconds() // 60)
        if minutes < 1:
            return "Posted less than a minute ago"
        if minutes < 60:
            return f"Posted about {minutes} minute{'s' if minutes != 1 else ''} ago"
        hours = minutes // 60
        if hours < 48:
            return f"Posted about {hours} hour{'s' if hours != 1 else ''} ago"
        days = hours // 24
        return f"Posted about {days} day{'s' if days != 1 else ''} ago"
    except (TypeError, ValueError):
        return "Could not determine"


def _context_explanation(
    text: str,
    context: dict[str, Any] | None,
    *,
    input_type: str = "text",
) -> dict[str, Any]:
    details = context if isinstance(context, dict) else {}
    default_checked = {
        "text": "Manually entered text",
        "image": "Image OCR from an uploaded file",
        "video": "Video audio transcript and video-frame OCR from an uploaded file",
        "consented_candidate": "Submitted text",
    }.get(input_type, "The supplied text")
    visible_links = []
    for value in details.get("visible_links", []):
        if isinstance(value, str) and urlparse(value).scheme in {"http", "https"}:
            visible_links.append(value)
    return {
        "overview": text[:320] + ("…" if len(text) > 320 else ""),
        "main_points": [], "separate_statements": [],
        "author": details.get("author") or "Not available",
        "timing": details.get("published_at") or details.get("published_text") or "Not available",
        "recency": _derived_recency(details.get("published_at")),
        "freshness": _derived_recency(details.get("published_at")),
        "recency_explanation": "Recency is calculated only when the selected post exposes a complete timestamp.",
        "assessment_scope": "One hybrid-model prediction was computed from the complete supplied text. Individual claims were not fact-checked.",
        "checked_material": details.get("extraction_scope") or default_checked,
        "original_post_url": details.get("original_post_url") or None,
        "relevant_links": list(dict.fromkeys(visible_links))[:8],
    }


def _screen(
    text: str,
    *,
    input_type: str,
    extraction_status: str,
    page_url: str | None = None,
    page_title: str | None = None,
    context: dict[str, Any] | None = None,
    capture_candidate: bool = False,
    retrieve_sources: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    analyzed_text = normalize_text(text)
    if not analyzed_text:
        raise HTTPException(status_code=422, detail="No usable text was provided for screening.")
    try:
        prediction = classify(analyzed_text).to_dict()
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail="The trained classifier is unavailable. Please try again after service recovery.") from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    inference_ms = (time.perf_counter() - started) * 1000
    retrieval_started = time.perf_counter()
    excluded_domain = urlparse(page_url).netloc if page_url else None
    explanation = _context_explanation(analyzed_text, context, input_type=input_type)
    if retrieve_sources:
        try:
            retrieval = retrieve_related_sources(analyzed_text, excluded_domain=excluded_domain)
        except Exception:
            retrieval = {"retrieval_status": "unavailable", "related_sources": []}
        fact_checks = {"status": "admin_only", "matches": [], "signal": None}
    else:
        retrieval = {"retrieval_status": "not_requested", "related_sources": []}
        fact_checks = {"status": "not_requested", "matches": [], "signal": None}
    linguistic_indicators = describe(prediction["linguistic_indicators"])
    prediction["linguistic_indicators"] = linguistic_indicators
    retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
    explanation["related_coverage"] = (
        "Retrieved links are related reading only; they have not been verified as supporting or debunking this text."
        if retrieval["related_sources"] else
        "No related links are available for this result. Retrieval does not affect the model prediction."
    )
    topic_suggestion = suggest_topic(analyzed_text)
    candidate_id = None
    if capture_candidate:
        try:
            candidate_id = database.create_candidate(
                text=analyzed_text,
                page_url=page_url,
                page_title=page_title,
                source_type=input_type,
                proposed_label=prediction["internal_label"],
                topic=topic_suggestion.topic,
                topic_confidence=topic_suggestion.confidence,
            )
            database.log_audit(
                "CANDIDATE_SUBMITTED_WITH_CONSENT",
                f"Candidate sample {candidate_id} submitted from {input_type} for human review.",
                "candidate-submission",
            )
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="Screening completed, but the candidate could not be saved for required review.",
            ) from None
    return {
        "timings_ms": {"inference": round(inference_ms, 3), "retrieval": round(retrieval_ms, 3)},
        **prediction,
        "analyzed_text": analyzed_text,
        "timestamp": _timestamp(),
        "input_type": input_type,
        "page_url": page_url,
        "page_title": page_title,
        "context": context or {},
        "context_explanation": explanation,
        "extraction_status": extraction_status,
        "retrieval_status": retrieval["retrieval_status"],
        "related_sources": retrieval["related_sources"],
        "fact_check_status": fact_checks["status"],
        "fact_check_matches": fact_checks["matches"],
        "decision_source": "screening_model",
        "decision_basis": None,
        "linguistic_indicators": linguistic_indicators,
        "candidate_sample_id": candidate_id,
        "topic_suggestion": topic_suggestion.to_dict(),
        "evidence_status": "missing" if capture_candidate else "not_captured",
        "model_scope_notice": config.MODEL_SCOPE_NOTICE,
        "disclaimer": config.DISCLAIMER,
    }


@app.post("/related-sources")
def related_sources(request: SourceLookupRequest) -> dict[str, Any]:
    analyzed_text = normalize_text(request.text)
    if not analyzed_text:
        raise HTTPException(status_code=422, detail="No usable text was provided for source lookup.")
    excluded_domain = urlparse(request.page_url).netloc if request.page_url else None
    try:
        result = retrieve_related_sources(analyzed_text, excluded_domain=excluded_domain)
    except Exception:
        result = {"retrieval_status": "unavailable", "related_sources": []}
    return {
        "retrieval_status": result["retrieval_status"],
        "related_sources": result["related_sources"],
        "classification_performed": False,
    }


async def _read_upload(file: UploadFile, expected_prefix: str) -> bytes:
    if not file.content_type or not file.content_type.lower().startswith(expected_prefix):
        raise HTTPException(status_code=415, detail=f"A supported {expected_prefix[:-1]} file is required.")
    contents = await file.read(config.MAX_MEDIA_BYTES + 1)
    await file.close()
    if not contents:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(contents) > config.MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="The uploaded file exceeds the configured limit.")
    return contents


@app.get("/health")
def health() -> dict[str, Any]:
    model = model_health()
    return {
        "backend": "available",
        "database": database.database_health(),
        "services": {
            **service_health(),
            "serper": "configured" if config.SERPER_API_KEY else "not_configured",
            "google_fact_check": "configured" if config.GOOGLE_FACT_CHECK_API_KEY else "not_configured",
        },
        "model": model,
        "model_status": model["status"],
        "timestamp": _timestamp(),
    }


@app.get("/ready")
def readiness(response: Response) -> dict[str, Any]:
    database_status = database.database_health()
    model = model_health()
    ready = database_status["status"] == "available" and model["status"] == "ready"
    if not ready:
        response.status_code = 503
    return {"ready": ready, "database": database_status, "model": model}


@app.post("/analyze")
def analyze(request: ScreenRequest) -> dict[str, Any]:
    return _screen(
        request.text,
        input_type="text",
        extraction_status="not_required",
        page_url=request.page_url,
        page_title=request.page_title,
        context=request.context,
        retrieve_sources=request.retrieve_sources,
    )


@app.post("/predict", deprecated=True)
def predict_compatibility(request: ScreenRequest) -> dict[str, Any]:
    return analyze(request)


@app.post("/analyze/image")
async def analyze_image(
    file: UploadFile = File(...),
    page_url: str | None = Form(default=None),
    page_title: str | None = Form(default=None),
    post_text: str | None = Form(default=None),
    context_json: str | None = Form(default=None),
    capture_candidate: bool = Form(default=False),
    retrieve_sources: bool = Form(default=False),
) -> dict[str, Any]:
    contents = await _read_upload(file, "image/")
    try:
        extraction = await run_in_threadpool(extract_image_text, contents)
    except MediaProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        post_context = json.loads(context_json) if context_json else {}
    except json.JSONDecodeError:
        post_context = {}
    readable_post_text = normalize_text(post_text or "")
    screening_text = "\n".join(part for part in [readable_post_text, extraction["ocr_text"]] if part)
    result = await run_in_threadpool(_screen,
        screening_text,
        input_type="image",
        extraction_status=extraction["extraction_status"],
        page_url=page_url,
        page_title=page_title,
        context=post_context,
        capture_candidate=False,
        retrieve_sources=retrieve_sources,
    )
    related_coverage = result["context_explanation"].get("related_coverage")
    post_context["extraction_scope"] = (
        "Facebook post caption and image OCR" if readable_post_text else "Image OCR"
    )
    result["context_explanation"] = _context_explanation(
        readable_post_text or extraction["ocr_text"], post_context, input_type="image"
    )
    result["context_explanation"]["related_coverage"] = related_coverage
    result["extraction"] = {"ocr_text": extraction["ocr_text"]}
    return result


@app.post("/analyze/video")
async def analyze_video(
    file: UploadFile = File(...),
    page_url: str | None = Form(default=None),
    page_title: str | None = Form(default=None),
    post_text: str | None = Form(default=None),
    context_json: str | None = Form(default=None),
    retrieve_sources: bool = Form(default=False),
) -> dict[str, Any]:
    contents = await _read_upload(file, "video/")
    suffix = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    if suffix not in {".mp4", ".webm", ".mov", ".mkv", ".avi"}:
        raise HTTPException(status_code=415, detail="The video file type is unsupported.")
    try:
        extraction = await run_in_threadpool(process_video, contents, suffix=suffix)
    except MediaProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        post_context = json.loads(context_json) if context_json else {}
    except json.JSONDecodeError:
        post_context = {}
    readable_post_text = normalize_text(post_text or "")
    screening_text = "\n".join(part for part in [readable_post_text, extraction["analyzed_text"]] if part)
    result = await run_in_threadpool(_screen,
        screening_text,
        input_type="video",
        extraction_status=extraction["extraction_status"],
        page_url=page_url,
        page_title=page_title,
        context=post_context,
        retrieve_sources=retrieve_sources,
    )
    related_coverage = result["context_explanation"].get("related_coverage")
    acquired = []
    if readable_post_text:
        acquired.append("Facebook post caption")
    if extraction["transcript_text"]:
        acquired.append("video audio transcript")
    if extraction["frame_ocr_text"]:
        acquired.append("video-frame OCR")
    post_context["extraction_scope"] = ", ".join(acquired) or "Video extraction"
    result["context_explanation"] = _context_explanation(
        readable_post_text or extraction["analyzed_text"], post_context, input_type="video"
    )
    result["context_explanation"]["related_coverage"] = related_coverage
    result["extraction"] = {
        "transcript_text": extraction["transcript_text"],
        "frame_ocr_text": extraction["frame_ocr_text"],
        "sampled_frames": extraction["sampled_frames"],
    }
    return result


@app.post("/candidates", status_code=201)
def submit_candidate(request: CandidateRequest) -> dict[str, Any]:
    result = _screen(
        request.text,
        input_type="consented_candidate",
        extraction_status="provided",
        page_url=request.page_url,
        page_title=request.page_title,
        context=request.context,
        capture_candidate=True,
        retrieve_sources=False,
    )
    return {
        "status": "submitted_for_human_review",
        "candidate_sample_id": result["candidate_sample_id"],
        "internal_label": result["internal_label"],
        "model_score": result["model_score"],
        "training_run_id": result["training_run_id"],
    }


def _token_signature(payload: str) -> str:
    if not config.SESSION_SECRET:
        raise HTTPException(status_code=503, detail="Administrator authentication is not configured.")
    return hmac.new(config.SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _create_token(username: str, role: str) -> str:
    payload = json.dumps(
        {"username": username, "role": role, "expires": int(time.time()) + config.SESSION_HOURS * 3600},
        separators=(",", ":"),
    )
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{encoded}.{_token_signature(encoded)}"


def _decode_token(token: str) -> dict[str, str]:
    try:
        encoded, signature = token.split(".", 1)
        if not hmac.compare_digest(_token_signature(encoded), signature):
            raise ValueError
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        if int(payload["expires"]) < int(time.time()):
            raise ValueError
        role = str(payload["role"])
        if role not in {"admin", "viewer"}:
            raise ValueError
        return {"username": str(payload["username"]), "role": role}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Administrator session is invalid or expired.") from None


def current_user(request: Request) -> dict[str, str]:
    token = request.cookies.get("suriph_admin_token")
    authorization = request.headers.get("Authorization", "")
    if not token and authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Administrator authentication is required.")
    return _decode_token(token)


def current_admin(user: dict[str, str] = Depends(current_user)) -> str:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="This account has view-only access.")
    return user["username"]


@app.post("/admin-api/login")
def admin_login(credentials: LoginRequest, response: Response) -> dict[str, str]:
    try:
        user = database.verify_admin(credentials.username.strip(), credentials.password)
    except Exception:
        raise HTTPException(status_code=503, detail="Administrator login is unavailable.") from None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid administrator credentials.")
    role = user.get("role", "admin")
    token = _create_token(user["username"], role)
    response.set_cookie(
        "suriph_admin_token",
        token,
        httponly=True,
        secure=config.APP_ENV == "production",
        samesite="strict",
        max_age=config.SESSION_HOURS * 3600,
    )
    try:
        database.log_audit("ADMIN_LOGIN", "Administrator signed in.", user["username"])
    except Exception:
        pass
    return {"status": "authenticated", "username": user["username"], "role": role}


@app.post("/admin-api/logout")
def admin_logout(response: Response, user: dict[str, str] = Depends(current_user)) -> dict[str, str]:
    response.delete_cookie("suriph_admin_token")
    try:
        database.log_audit("ADMIN_LOGOUT", "Administrative user signed out.", user["username"])
    except Exception:
        pass
    return {"status": "logged_out"}


@app.get("/admin-api/check-auth")
def check_auth(user: dict[str, str] = Depends(current_user)) -> dict[str, Any]:
    return {"authenticated": True, **user}


def _database_or_503(operation):
    try:
        return operation()
    except Exception:
        raise HTTPException(status_code=503, detail="The database service is unavailable.") from None


@app.get("/admin-api/candidates")
def admin_candidates(
    limit: int = 100,
    topic: str | None = None,
    validation_status: str | None = None,
    evidence_status: str | None = None,
    _username: str = Depends(current_admin),
):
    if topic and topic not in config.TOPIC_CATEGORIES:
        raise HTTPException(status_code=422, detail="Unknown topic filter.")
    if validation_status and validation_status not in {"pending", "approved", "needs_revision", "excluded"}:
        raise HTTPException(status_code=422, detail="Unknown validation status filter.")
    if evidence_status and evidence_status not in {"missing", "unverified", "verified"}:
        raise HTTPException(status_code=422, detail="Unknown evidence status filter.")
    return {
        "candidates": _database_or_503(
            lambda: database.list_candidates(
                min(limit, 10_000),
                topic=topic,
                validation_status=validation_status,
                evidence_status=evidence_status,
            )
        )
    }


@app.get("/admin-api/candidate-summary")
def admin_candidate_summary(_username: str = Depends(current_admin)):
    return _database_or_503(database.candidate_topic_summary)


def _safe_spreadsheet_value(value: Any) -> Any:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@app.get("/admin-api/candidates-export")
def admin_export_candidates(
    format: Literal["csv", "xlsx"] = "csv",
    topic: str | None = None,
    validation_status: str | None = None,
    evidence_status: str | None = None,
    _username: str = Depends(current_admin),
):
    if topic and topic not in config.TOPIC_CATEGORIES:
        raise HTTPException(status_code=422, detail="Unknown topic filter.")
    rows = _database_or_503(
        lambda: database.export_candidates(
            topic=topic,
            validation_status=validation_status,
            evidence_status=evidence_status,
        )
    )
    rows = [{key: _safe_spreadsheet_value(value) for key, value in row.items()} for row in rows]
    filename = f"suriph-candidates-{datetime.now(timezone.utc).date().isoformat()}.{format}"
    fieldnames = list(rows[0]) if rows else [
        "candidate_sample_id", "text", "input_type", "language", "topic",
        "topic_confidence", "topic_review_status", "proposed_label",
        "validation_status", "training_status", "evidence_status", "evidence_urls",
        "source_url", "page_title", "claim_group_id", "submitted_at",
    ]
    if format == "csv":
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        content = io.BytesIO(stream.getvalue().encode("utf-8-sig"))
        media_type = "text/csv; charset=utf-8"
    else:
        try:
            import pandas as pd
            content = io.BytesIO()
            pd.DataFrame(rows, columns=fieldnames).to_excel(content, index=False, engine="openpyxl")
            content.seek(0)
        except ImportError:
            raise HTTPException(status_code=503, detail="Excel export support is not installed.") from None
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return StreamingResponse(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/admin-api/candidates/{candidate_id}/review")
def admin_review_candidate(
    candidate_id: int,
    review: CandidateReviewRequest,
    username: str = Depends(current_admin),
):
    if review.decision == "approve" and not review.proposed_label:
        raise HTTPException(status_code=422, detail="Approved candidates require a final proposed label.")
    if review.decision == "approve" and (not review.language or not review.topic or not review.claim_group_id):
        raise HTTPException(
            status_code=422,
            detail="Approved candidates require reviewed language, topic, and claim group ID.",
        )
    if review.decision == "approve" and review.topic not in config.TOPIC_CATEGORIES:
        raise HTTPException(status_code=422, detail="Topic must use one of the eight paper-defined categories.")
    try:
        result = database.review_candidate(
            candidate_id,
            decision=review.decision,
            proposed_label=review.proposed_label,
            notes=review.notes,
            reviewer=username,
            language=review.language,
            topic=review.topic,
            claim_group_id=review.claim_group_id,
        )
        database.log_audit(
            "CANDIDATE_REVIEWED",
            f"Candidate {candidate_id} marked {review.decision}.",
            username,
        )
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.get("/admin-api/candidates/{candidate_id}/evidence")
def admin_candidate_evidence(candidate_id: int, _username: str = Depends(current_admin)):
    return {"evidence": _database_or_503(lambda: database.list_evidence(candidate_id))}


@app.get("/admin-api/candidates/{candidate_id}/annotations")
def admin_candidate_annotations(candidate_id: int, _username: str = Depends(current_admin)):
    return {"annotations": _database_or_503(lambda: database.list_annotations(candidate_id))}


@app.post("/admin-api/candidates/{candidate_id}/annotations", status_code=201)
def admin_add_annotation(candidate_id: int, payload: IndependentAnnotationRequest, username: str = Depends(current_admin)):
    try:
        annotation_id = database.add_independent_annotation(
            candidate_id,
            reviewer=username,
            proposed_label=payload.proposed_label,
            annotation_round=payload.annotation_round,
            evidence_sufficient=payload.evidence_sufficient,
            notes=payload.notes,
        )
        database.log_audit("INDEPENDENT_ANNOTATION_ADDED", f"Annotation {annotation_id} added to candidate {candidate_id}.", username)
        return {"annotation_id": annotation_id}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.post("/admin-api/candidates/{candidate_id}/evidence", status_code=201)
def admin_add_evidence(
    candidate_id: int,
    evidence: EvidenceRequest,
    username: str = Depends(current_admin),
):
    try:
        evidence_id = database.add_evidence(
            candidate_id,
            source_url=evidence.source_url,
            publisher=evidence.publisher,
            rating=evidence.rating,
            claim_match_status=evidence.claim_match_status,
            notes=evidence.notes,
            reviewer=username,
        )
        database.log_audit("EVIDENCE_ADDED", f"Evidence {evidence_id} added to candidate {candidate_id}.", username)
        return {"evidence_record_id": evidence_id}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@app.get("/admin-api/candidates/{candidate_id}/fact-check-search")
def admin_fact_check_search(candidate_id: int, _username: str = Depends(current_admin)):
    candidate = _database_or_503(lambda: database.get_candidate(candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate sample was not found.")
    return search_fact_checks(candidate["text_content"])


@app.get("/admin-api/dataset-versions")
def admin_dataset_versions(_username: str = Depends(current_admin)):
    return {"dataset_versions": _database_or_503(database.list_dataset_versions)}


@app.get("/admin-api/dataset-versions/{version_id}/composition")
def admin_dataset_composition(version_id: int, _username: str = Depends(current_admin)):
    return {
        "composition": _database_or_503(lambda: database.dataset_composition(version_id)),
        "targets": {
            "total_taglish": config.MIN_TAGLISH_SAMPLES,
            "per_class": config.MIN_SAMPLES_PER_CLASS,
            "per_topic": config.MIN_SAMPLES_PER_TOPIC,
            "per_topic_class": config.MIN_SAMPLES_PER_TOPIC_CLASS,
            "topics": config.TOPIC_CATEGORIES,
        },
    }


@app.post("/admin-api/dataset-versions/import", status_code=201)
async def admin_import_validated_dataset(
    version_name: str = Form(min_length=1, max_length=120),
    file: UploadFile = File(...),
    username: str = Depends(current_admin),
):
    filename = (file.filename or "").lower()
    if not filename.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=415, detail="Upload a CSV or XLSX validated dataset.")
    contents = await file.read(config.MAX_MEDIA_BYTES + 1)
    await file.close()
    if not contents:
        raise HTTPException(status_code=422, detail="The validated dataset file is empty.")
    if len(contents) > config.MAX_MEDIA_BYTES:
        raise HTTPException(status_code=413, detail="The validated dataset file is too large.")
    try:
        import pandas as pd
        frame = pd.read_excel(io.BytesIO(contents)) if filename.endswith(".xlsx") else pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"The dataset file could not be read: {exc}") from None
    frame.columns = [re.sub(r"[^a-z0-9]+", "_", str(column).strip().casefold()).strip("_") for column in frame.columns]
    if "text" not in frame.columns:
        raise HTTPException(status_code=422, detail="The dataset requires a text column.")
    label_column = next((name for name in ("label", "final_label", "proposed_label") if name in frame.columns), None)
    evidence_column = next((name for name in ("evidence_url", "evidence_urls") if name in frame.columns), None)
    required = {"topic", "claim_group_id"}
    missing = sorted(required - set(frame.columns))
    if not label_column:
        missing.append("label")
    if not evidence_column:
        missing.append("evidence_url")
    if missing:
        raise HTTPException(status_code=422, detail="Missing required columns: " + ", ".join(missing))

    def cell(value: Any) -> str:
        if pd.isna(value):
            return ""
        return str(value).strip()

    imported_rows = []
    for row_number, (_, source) in enumerate(frame.iterrows(), start=2):
        text_value = normalize_text(cell(source.get("text")))
        raw_label = cell(source.get(label_column))
        label_map = {"1": "Misleading", "misleading": "Misleading", "0": "Non-Misleading", "non-misleading": "Non-Misleading", "non misleading": "Non-Misleading"}
        label = label_map.get(raw_label.casefold())
        topic = cell(source.get("topic"))
        claim_group_id = cell(source.get("claim_group_id"))
        evidence_url = cell(source.get(evidence_column)).split(" | ", 1)[0].split(" [", 1)[0]
        partition = cell(source.get("partition_name")).casefold() if "partition_name" in frame.columns else ""
        if not text_value:
            raise HTTPException(status_code=422, detail=f"Row {row_number}: text is required.")
        if not label:
            raise HTTPException(status_code=422, detail=f"Row {row_number}: label must be Misleading/Non-Misleading or 1/0.")
        if topic not in config.TOPIC_CATEGORIES:
            raise HTTPException(status_code=422, detail=f"Row {row_number}: topic must use one of the eight paper-defined categories.")
        if not claim_group_id:
            raise HTTPException(status_code=422, detail=f"Row {row_number}: claim_group_id is required.")
        parsed_evidence = urlparse(evidence_url)
        if parsed_evidence.scheme not in {"http", "https"} or not parsed_evidence.netloc:
            raise HTTPException(status_code=422, detail=f"Row {row_number}: a valid evidence URL is required.")
        if partition and partition not in {"train", "validation", "test"}:
            raise HTTPException(status_code=422, detail=f"Row {row_number}: partition_name must be train, validation, or test.")
        imported_rows.append({
            "text": text_value,
            "label": label,
            "topic": topic,
            "claim_group_id": claim_group_id,
            "evidence_url": evidence_url,
            "partition_name": partition or None,
            "language": cell(source.get("language")) or "Taglish",
            "source_url": cell(source.get("source_url")) or None,
            "page_title": cell(source.get("page_title")) or None,
            "publisher": cell(source.get("publisher")) or None,
            "rating": cell(source.get("rating")) or None,
        })
    try:
        result = database.import_validated_dataset(version_name, imported_rows, created_by=username)
        database.log_audit("VALIDATED_DATASET_IMPORTED", f"Imported {len(imported_rows)} rows into dataset version {result['dataset_version_id']}.", username)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.post("/admin-api/dataset-versions", status_code=201)
def admin_create_dataset_version(
    payload: DatasetVersionRequest, username: str = Depends(current_admin)
):
    version_id = _database_or_503(
        lambda: database.create_dataset_version(payload.version_name, payload.description, username)
    )
    database.log_audit("DATASET_VERSION_CREATED", f"Dataset version {version_id} created.", username)
    return {"dataset_version_id": version_id}


@app.post("/admin-api/dataset-versions/{version_id}/items", status_code=201)
def admin_add_dataset_item(
    version_id: int, payload: DatasetItemRequest, username: str = Depends(current_admin)
):
    try:
        item_id = database.add_dataset_item(
            version_id,
            candidate_id=payload.candidate_sample_id,
            final_label=payload.final_label,
            partition_name=payload.partition_name,
            claim_group_id=payload.claim_group_id,
        )
        database.log_audit("DATASET_ITEM_ADDED", f"Dataset item {item_id} added to version {version_id}.", username)
        return {"dataset_item_id": item_id}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.post("/admin-api/dataset-versions/{version_id}/items/bulk")
def admin_bulk_add_dataset_items(version_id: int, username: str = Depends(current_admin)):
    try:
        result = database.bulk_add_approved_candidates(version_id)
        database.log_audit(
            "DATASET_ITEMS_BULK_ADDED",
            f"Added {result['added']} approved candidates to dataset version {version_id}.",
            username,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.post("/admin-api/dataset-versions/{version_id}/approve")
def admin_approve_dataset_version(version_id: int, username: str = Depends(current_admin)):
    try:
        database.approve_dataset_version(version_id)
        database.log_audit("DATASET_VERSION_APPROVED", f"Dataset version {version_id} approved.", username)
        return {"status": "approved"}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.get("/admin-api/model-versions")
def admin_model_versions(_user: dict[str, str] = Depends(current_user)):
    return {"model_versions": _database_or_503(database.list_model_versions)}


@app.get("/admin-api/training-runs")
def admin_training_runs(_username: str = Depends(current_admin)):
    return {"training_runs": _database_or_503(database.list_training_runs)}


@app.post("/admin-api/training-runs", status_code=202)
def admin_queue_training(payload: RetrainingRequest, username: str = Depends(current_admin)):
    raise HTTPException(status_code=410, detail="This deployment is pinned to the verified model_4 hybrid pipeline. Training, model registration and activation are disabled.")


@app.post("/admin-api/model-versions", status_code=201)
def admin_register_model(payload: ModelVersionRequest, username: str = Depends(current_admin)):
    raise HTTPException(status_code=410, detail="This deployment is pinned to the verified model_4 hybrid pipeline. Training, model registration and activation are disabled.")


@app.post("/admin-api/model-versions/{model_id}/review")
def admin_review_model(
    model_id: int, payload: ModelReviewRequest, username: str = Depends(current_admin)
):
    try:
        database.review_model_version(model_id, payload.decision, username)
        database.log_audit("MODEL_VERSION_REVIEWED", f"Model {model_id} marked {payload.decision}.", username)
        return {"status": payload.decision}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.post("/admin-api/model-versions/{model_id}/activate")
def admin_activate_model(model_id: int, username: str = Depends(current_admin)):
    raise HTTPException(status_code=410, detail="This deployment is pinned to the verified model_4 hybrid pipeline. Training, model registration and activation are disabled.")


@app.get("/admin-api/audit-logs")
def admin_audit_logs(limit: int = 100, _username: str = Depends(current_admin)):
    return {"audit_logs": _database_or_503(lambda: database.list_audits(min(limit, 500)))}


@app.get("/admin-api/stats")
def admin_stats(_user: dict[str, str] = Depends(current_user)):
    return {"stats": _database_or_503(database.sprint_stats)}


@app.get("/admin-api/system-status")
def admin_system_status(_user: dict[str, str] = Depends(current_user)):
    return health()
