"""FastAPI application for the SuriPH Sprint 1 working prototype."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
try:
    from . import database
    from .fact_check import search_fact_checks
    from .media_processing import MediaProcessingError, extract_image_text, process_video, service_health
    from .mock_classifier import classify, normalize_text
    from .retrieval import retrieve_related_sources
except ImportError:  # Supports the legacy test runner that adds src/ to sys.path.
    import database
    from fact_check import search_fact_checks
    from media_processing import MediaProcessingError, extract_image_text, process_video, service_health
    from mock_classifier import classify, normalize_text
    from retrieval import retrieve_related_sources


class ScreenRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)
    page_url: str | None = Field(default=None, max_length=4_000)
    page_title: str | None = Field(default=None, max_length=500)
    context: dict[str, Any] | None = None


class CandidateRequest(ScreenRequest):
    pass


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=500)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    migration = database.migrate()
    if migration["status"] == "available":
        try:
            created = database.ensure_bootstrap_admin()
            if created:
                database.log_audit("ADMIN_BOOTSTRAPPED", "Initial administrator created.")
        except Exception:
            pass
    yield


app = FastAPI(title="SuriPH Working Prototype API", version="1.0.0-sprint1", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(config.CORS_ORIGINS),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _context_explanation(text: str, context: dict[str, Any] | None) -> dict[str, Any]:
    details = context or {}
    cleaned_text = re.sub(r"\bSee (?:more|less)\b", " ", text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r"\bMay be an image of.*?text that says\b", " ", cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r"\bShared post\b(?:\s+[\d.KMB]+){1,5}", " ", cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r"^.{0,100}?\bFollow\s+(?:\d+\s*[mhdw]|Yesterday)\b[·\s]*", "", cleaned_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()
    raw_sentences = [
        part.strip(" -|Â·")
        for part in re.split(r"(?<=[.!?])\s+|\n+|\s+[|•]\s+", cleaned_text)
        if len(part.strip()) >= 20
    ]
    sentences: list[str] = []
    seen: set[str] = set()
    for sentence in raw_sentences:
        sentence = re.sub(r"\s+", " ", sentence).strip()
        key = re.sub(r"[^a-z0-9]+", " ", sentence.casefold()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        sentences.append(sentence[:320])
        if len(sentences) == 4:
            break

    # Facebook often repeats the caption inside accessibility text and appends
    # dates, engagement counts, page names, and "Read more" controls. Remove
    # those fragments before deciding how many real statements the post has.
    months = {
        "january", "february", "march", "april", "may", "june", "july",
        "august", "september", "october", "november", "december",
    }
    noise_words = {
        "read", "more", "less", "follow", "shared", "post", "news", "update",
        "verified", "account", "com", "www", "http", "https",
    }
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "of",
        "for", "from", "with", "this", "that", "is", "are", "was", "were",
    }

    def statement_tokens(value: str) -> set[str]:
        words = re.findall(r"[a-zA-Z]{3,}", value.casefold())
        return {word for word in words if word not in months | noise_words | stop_words}

    distinct_sentences: list[str] = []
    distinct_tokens: list[set[str]] = []
    for sentence in sentences:
        sentence = re.split(r"\bRead\s+(?:more|less)\b", sentence, maxsplit=1, flags=re.IGNORECASE)[0]
        sentence = re.sub(
            r"^(?:\s*['\"]?\d{0,2}\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)[a-z]*\s*\d{0,2}\s*,?\s*\d{4}\W*)+",
            "",
            sentence,
            flags=re.IGNORECASE,
        ).strip(" '\".,-|…")
        tokens = statement_tokens(sentence)
        if len(tokens) < 4:
            continue
        duplicate = False
        for previous in distinct_tokens:
            overlap = len(tokens & previous) / max(1, min(len(tokens), len(previous)))
            if overlap >= 0.65:
                duplicate = True
                break
        if duplicate:
            continue
        distinct_sentences.append(sentence[:280])
        distinct_tokens.append(tokens)
        if len(distinct_sentences) == 3:
            break
    sentences = distinct_sentences

    overview = (sentences[0] if sentences else cleaned_text[:320].strip()) or "Not enough readable content was available to describe the topic."
    # Do not repeat the overview in the claim list. Each remaining statement is
    # kept separate so mixed-accuracy posts are not treated as one claim.
    main_points = sentences[1:]
    timing = details.get("published_text") or details.get("published_at") or "No clear posting date was found."
    freshness = details.get("freshness") or "The recency could not be confirmed from the visible post."
    author = details.get("author") or "The visible author could not be identified."
    statement_count = max(1, len(sentences))
    separate_statements = [
        {"number": index, "statement": sentence}
        for index, sentence in enumerate(sentences, start=1)
    ] if len(sentences) > 1 else []
    if timing == "No clear posting date was found.":
        recency_explanation = "No clear posting date was visible, so SuriPH could not confirm whether this is new, old, or reposted content."
    elif "older" in freshness.casefold():
        recency_explanation = "This appears to be an older post. If it is being shared again now, its original date and event timeline may change how the claims should be understood."
    else:
        recency_explanation = "This appears recent based on the visible timestamp, but a recent upload does not prove the event itself is new. The event date and original source still need to match the claims."
    assessment_scope = (
        f"SuriPH identified {statement_count} separate statements and checked each one individually, because an accurate statement does not automatically make every other statement in the same post accurate."
        if statement_count > 1
        else "SuriPH found one main checkable statement after removing repeated captions and Facebook interface text."
    )
    checked_material = details.get("extraction_scope") or "The readable post text and available media content"
    return {
        "overview": overview,
        "main_points": main_points,
        "separate_statements": separate_statements,
        "author": author,
        "timing": timing,
        "freshness": freshness,
        "recency_explanation": recency_explanation,
        "assessment_scope": assessment_scope,
        "checked_material": checked_material,
    }


def _screen(
    text: str,
    *,
    input_type: str,
    extraction_status: str,
    page_url: str | None = None,
    page_title: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    analyzed_text = normalize_text(text)
    if not analyzed_text:
        raise HTTPException(status_code=422, detail="No usable text was provided for screening.")
    prediction = classify(analyzed_text).to_dict()
    excluded_domain = urlparse(page_url).netloc if page_url else None
    explanation = _context_explanation(analyzed_text, context)
    retrieval_query = " ".join([explanation["overview"], *explanation.get("main_points", [])])
    retrieval = retrieve_related_sources(retrieval_query, excluded_domain=excluded_domain)
    fact_checks = search_fact_checks(retrieval_query)
    fact_check_signal = fact_checks.get("signal")
    if fact_check_signal:
        prediction["internal_label"] = fact_check_signal["internal_label"]
        prediction["public_label"] = fact_check_signal["public_label"]
        prediction["temporary_score"] = fact_check_signal["confidence"]
    if retrieval["retrieval_status"] == "available":
        explanation["related_coverage"] = f"Related reporting was found from {len(retrieval['related_sources'])} credible source(s)."
    elif retrieval["retrieval_status"] == "disabled":
        explanation["related_coverage"] = "Related-source lookup is currently turned off, so similar coverage was not compared for this result."
    else:
        explanation["related_coverage"] = "No matching credible coverage was found for comparison."
    return {
        **prediction,
        "confidence": prediction["temporary_score"],
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
        "decision_source": "google_fact_check" if fact_check_signal else "screening_model",
        "decision_basis": fact_check_signal["basis"] if fact_check_signal else None,
        "disclaimer": config.DISCLAIMER,
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
    return {
        "backend": "available",
        "database": database.database_health(),
        "services": {
            **service_health(),
            "serper": "configured" if config.SERPER_API_KEY else "not_configured",
            "google_fact_check": "configured" if config.GOOGLE_FACT_CHECK_API_KEY else "not_configured",
        },
        "model_status": config.MODEL_STATUS,
        "timestamp": _timestamp(),
    }


@app.post("/analyze")
def analyze(request: ScreenRequest) -> dict[str, Any]:
    return _screen(
        request.text,
        input_type="text",
        extraction_status="not_required",
        page_url=request.page_url,
        page_title=request.page_title,
        context=request.context,
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
) -> dict[str, Any]:
    contents = await _read_upload(file, "image/")
    try:
        extraction = extract_image_text(contents)
    except MediaProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        post_context = json.loads(context_json) if context_json else {}
    except json.JSONDecodeError:
        post_context = {}
    readable_post_text = normalize_text(post_text or "")
    screening_text = "\n".join(part for part in [readable_post_text, extraction["ocr_text"]] if part)
    result = _screen(
        screening_text,
        input_type="image",
        extraction_status=extraction["extraction_status"],
        page_url=page_url,
        page_title=page_title,
        context=post_context,
    )
    related_coverage = result["context_explanation"].get("related_coverage")
    result["context_explanation"] = _context_explanation(readable_post_text or extraction["ocr_text"], post_context)
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
) -> dict[str, Any]:
    contents = await _read_upload(file, "video/")
    suffix = Path(file.filename or "video.mp4").suffix.lower() or ".mp4"
    if suffix not in {".mp4", ".webm", ".mov", ".mkv", ".avi"}:
        raise HTTPException(status_code=415, detail="The video file type is unsupported.")
    try:
        extraction = process_video(contents, suffix=suffix)
    except MediaProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    try:
        post_context = json.loads(context_json) if context_json else {}
    except json.JSONDecodeError:
        post_context = {}
    readable_post_text = normalize_text(post_text or "")
    screening_text = "\n".join(part for part in [readable_post_text, extraction["analyzed_text"]] if part)
    result = _screen(
        screening_text,
        input_type="video",
        extraction_status=extraction["extraction_status"],
        page_url=page_url,
        page_title=page_title,
        context=post_context,
    )
    related_coverage = result["context_explanation"].get("related_coverage")
    result["context_explanation"] = _context_explanation(readable_post_text or extraction["analyzed_text"], post_context)
    result["context_explanation"]["related_coverage"] = related_coverage
    result["extraction"] = {
        "transcript_text": extraction["transcript_text"],
        "frame_ocr_text": extraction["frame_ocr_text"],
        "sampled_frames": extraction["sampled_frames"],
    }
    return result


@app.post("/candidates", status_code=201)
def submit_candidate(request: CandidateRequest) -> dict[str, Any]:
    try:
        candidate_id = database.create_candidate(
            text=normalize_text(request.text),
            page_url=request.page_url,
            page_title=request.page_title,
        )
        database.log_audit(
            "CANDIDATE_SUBMITTED", f"Candidate sample {candidate_id} submitted.", "public-user"
        )
    except Exception:
        raise HTTPException(
            status_code=503, detail="Candidate submission is unavailable because the database is offline."
        ) from None
    return {
        "candidate_sample_id": candidate_id,
        "validation_status": "pending",
        "training_status": "not_training_data",
    }


def _token_signature(payload: str) -> str:
    if not config.SESSION_SECRET:
        raise HTTPException(status_code=503, detail="Administrator authentication is not configured.")
    return hmac.new(config.SESSION_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


def _create_token(username: str) -> str:
    payload = json.dumps(
        {"username": username, "expires": int(time.time()) + config.SESSION_HOURS * 3600},
        separators=(",", ":"),
    )
    encoded = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    return f"{encoded}.{_token_signature(encoded)}"


def _decode_token(token: str) -> str:
    try:
        encoded, signature = token.split(".", 1)
        if not hmac.compare_digest(_token_signature(encoded), signature):
            raise ValueError
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        if int(payload["expires"]) < int(time.time()):
            raise ValueError
        return str(payload["username"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Administrator session is invalid or expired.") from None


def current_admin(request: Request) -> str:
    token = request.cookies.get("suriph_admin_token")
    authorization = request.headers.get("Authorization", "")
    if not token and authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Administrator authentication is required.")
    return _decode_token(token)


@app.post("/admin-api/login")
def admin_login(credentials: LoginRequest, response: Response) -> dict[str, str]:
    try:
        user = database.verify_admin(credentials.username.strip(), credentials.password)
    except Exception:
        raise HTTPException(status_code=503, detail="Administrator login is unavailable.") from None
    if not user:
        raise HTTPException(status_code=401, detail="Invalid administrator credentials.")
    token = _create_token(user["username"])
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
    return {"status": "authenticated", "token": token, "username": user["username"]}


@app.post("/admin-api/logout")
def admin_logout(response: Response, username: str = Depends(current_admin)) -> dict[str, str]:
    response.delete_cookie("suriph_admin_token")
    try:
        database.log_audit("ADMIN_LOGOUT", "Administrator signed out.", username)
    except Exception:
        pass
    return {"status": "logged_out"}


@app.get("/admin-api/check-auth")
def check_auth(username: str = Depends(current_admin)) -> dict[str, Any]:
    return {"authenticated": True, "username": username}


def _database_or_503(operation):
    try:
        return operation()
    except Exception:
        raise HTTPException(status_code=503, detail="The database service is unavailable.") from None


@app.get("/admin-api/candidates")
def admin_candidates(limit: int = 100, _username: str = Depends(current_admin)):
    return {"candidates": _database_or_503(lambda: database.list_candidates(min(limit, 500)))}


@app.get("/admin-api/audit-logs")
def admin_audit_logs(limit: int = 100, _username: str = Depends(current_admin)):
    return {"audit_logs": _database_or_503(lambda: database.list_audits(min(limit, 500)))}


@app.get("/admin-api/stats")
def admin_stats(_username: str = Depends(current_admin)):
    return {"stats": _database_or_503(database.sprint_stats)}


@app.get("/admin-api/system-status")
def admin_system_status(_username: str = Depends(current_admin)):
    return health()
