"""Environment-backed configuration for the SuriPH API."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from urllib.parse import quote_plus, urlparse

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
if os.getenv("SURI_APP_ENV") != "production" and os.getenv("SURI_LOAD_ENV_FILES", "true").lower() == "true":
    # Explicit environment values always win, including in CI and containers.
    load_dotenv(BASE_DIR / ".env.local", override=False)
    load_dotenv(BASE_DIR / ".env", override=False)


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


APP_ENV = _env("SURI_APP_ENV", "development")
APP_HOST = _env("SURI_APP_HOST", "127.0.0.1")
APP_PORT = _env_int("SURI_APP_PORT", 8000)
DATABASE_URL = _env("SURI_DATABASE_URL")
DB_HOST = _env("SURI_DB_HOST")
DB_PORT = _env_int("SURI_DB_PORT", 3306)
DB_USER = _env("SURI_DB_USER", _env("MARIADB_USER"))
DB_PASSWORD = os.getenv("SURI_DB_PASSWORD", os.getenv("MARIADB_PASSWORD", ""))
DB_NAME = _env("SURI_DB_NAME", _env("MARIADB_DATABASE", "suriph"))
_sqlite_path_text = _env("SURI_SQLITE_PATH")
_sqlite_path = Path(_sqlite_path_text) if _sqlite_path_text else Path("data/runtime-sqlite/suriph.db")
DB_PATH = _sqlite_path if _sqlite_path.is_absolute() else BASE_DIR / _sqlite_path
DB_CONNECT_TIMEOUT = _env_int("SURI_DB_CONNECT_TIMEOUT", 5)
if not DATABASE_URL and DB_HOST and DB_USER:
    DATABASE_URL = (
        f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}@"
        f"{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
DB_ENGINE = "mariadb" if DATABASE_URL.startswith(("mysql", "mariadb")) else "sqlite"
ADMIN_BOOTSTRAP_USERNAME = _env("SURI_ADMIN_USERNAME")
ADMIN_BOOTSTRAP_PASSWORD = os.getenv("SURI_ADMIN_PASSWORD", "")
VIEWER_BOOTSTRAP_USERNAME = _env("SURI_VIEWER_USERNAME")
VIEWER_BOOTSTRAP_PASSWORD = os.getenv("SURI_VIEWER_PASSWORD", "")
SESSION_SECRET = os.getenv("SURI_SESSION_SECRET", "")
SESSION_HOURS = _env_int("SURI_SESSION_HOURS", 8)
MIN_TAGLISH_SAMPLES = _env_int("SURI_MIN_TAGLISH_SAMPLES", 4000)
MIN_SAMPLES_PER_CLASS = _env_int("SURI_MIN_SAMPLES_PER_CLASS", 2000)
MIN_SAMPLES_PER_TOPIC = _env_int("SURI_MIN_SAMPLES_PER_TOPIC", 500)
MIN_SAMPLES_PER_TOPIC_CLASS = _env_int("SURI_MIN_SAMPLES_PER_TOPIC_CLASS", 250)
MIN_TRAIN_SAMPLES = _env_int("SURI_MIN_TRAIN_SAMPLES", 2800)
MIN_VALIDATION_SAMPLES = _env_int("SURI_MIN_VALIDATION_SAMPLES", 600)
MIN_TEST_SAMPLES = _env_int("SURI_MIN_TEST_SAMPLES", 600)
ENFORCE_PAPER_DATASET = _env("SURI_ENFORCE_PAPER_DATASET", "true").lower() in {"1", "true", "yes", "on"}
PILOT_ANNOTATORS = _env_int("SURI_PILOT_ANNOTATORS", 4)
MIN_PILOT_SAMPLES = _env_int("SURI_MIN_PILOT_SAMPLES", 100)
MAX_PILOT_SAMPLES = _env_int("SURI_MAX_PILOT_SAMPLES", 150)
TOPIC_CATEGORIES = (
    "Politics, Governance, and Elections",
    "Health and Medicine",
    "Economy, Finance, and Employment",
    "Public Safety, Disaster, and Security",
    "Science, Technology, and Environment",
    "Education and Social Issues",
    "Entertainment and Public Figures",
    "Other and General",
)
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
SERPER_ENABLED = _env("SERPER_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
SERPER_TIMEOUT_SECONDS = _env_int("SERPER_TIMEOUT_SECONDS", 8)
SERPER_MAX_RESULTS = _env_int("SERPER_MAX_RESULTS", 3)
GOOGLE_FACT_CHECK_API_KEY = os.getenv("GOOGLE_FACT_CHECK_API_KEY", "").strip()
GOOGLE_FACT_CHECK_ENABLED = _env("GOOGLE_FACT_CHECK_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
GOOGLE_FACT_CHECK_TIMEOUT_SECONDS = _env_int("GOOGLE_FACT_CHECK_TIMEOUT_SECONDS", 8)
GOOGLE_FACT_CHECK_MAX_RESULTS = _env_int("GOOGLE_FACT_CHECK_MAX_RESULTS", 3)
MAX_MEDIA_BYTES = _env_int("SURI_MAX_MEDIA_BYTES", 50 * 1024 * 1024)
OCR_LANGUAGES = tuple(
    language.strip()
    for language in _env("SURI_OCR_LANGUAGES", "en,tl").split(",")
    if language.strip()
)
OCR_GPU = _env("SURI_OCR_GPU", "false").lower() in {"1", "true", "yes"}
WHISPER_MODEL_NAME = _env("SURI_WHISPER_MODEL", "tiny")
VIDEO_FRAME_INTERVAL_SECONDS = _env_int("SURI_VIDEO_FRAME_INTERVAL_SECONDS", 3)
VIDEO_MAX_FRAMES = _env_int("SURI_VIDEO_MAX_FRAMES", 3)
TEMP_MEDIA_DIR = Path(
    _env("SURI_TEMP_MEDIA_DIR", str(Path(tempfile.gettempdir()) / "suriph-media"))
)
MEDIA_MODEL_DIR = Path(_env("SURI_MEDIA_MODEL_DIR", str(BASE_DIR / "data" / "runtime-models")))
_cors_default = "http://localhost:5173,http://127.0.0.1:5173"
CORS_ORIGINS = tuple(
    origin.strip()
    for origin in _env("SURI_CORS_ORIGINS", _cors_default).split(",")
    if origin.strip()
)
TRUSTED_HOSTS = tuple(
    host.strip() for host in _env("SURI_TRUSTED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
    if host.strip()
)
DISCLAIMER = (
    "This is a model prediction and can be wrong. Its score is not calibrated certainty or proof that a claim is true or false. "
    "Related links are not automatically supporting or debunking evidence. Check original sources, dates and context."
)
MODEL_SCOPE_NOTICE = (
    "The model was verified against its saved article-like test set. Brief or out-of-distribution text can receive "
    "unreliable, extreme scores; review the exact analyzed text and independent sources."
)

MODEL_PROFILE = _env("SURI_MODEL_PROFILE", "20261011T235112Z")
_artifact_dir_text = _env("SURI_MODEL_ARTIFACT_DIR")
_artifact_dir = Path(_artifact_dir_text) if _artifact_dir_text else None
MODEL_ARTIFACT_DIR = (
    (_artifact_dir if _artifact_dir.is_absolute() else BASE_DIR / _artifact_dir).resolve()
    if _artifact_dir is not None else None
)
MODEL_DEVICE = _env("SURI_MODEL_DEVICE", "auto")
MODEL_CPU_THREADS = _env_int("SURI_MODEL_CPU_THREADS", 4)
MAX_TEXT_CHARACTERS = 1_000_000
MODEL_REQUIRED = _env("SURI_MODEL_REQUIRED", "true").lower() in {"1", "true", "yes", "on"}
MODEL_WARMUP = _env("SURI_MODEL_WARMUP", "true" if APP_ENV == "production" else "false").lower() == "true"
TRAINING_ENABLED = False  # This deployment serves only the pinned, already-trained model_4.


def validate_runtime_config() -> None:
    """Reject unsafe production configuration before accepting traffic."""
    if APP_ENV != "production":
        return
    errors = []
    def unsafe_secret(value: str, minimum: int) -> bool:
        return len(value) < minimum or value.lower().startswith(("replace-", "generate-", "changeme", "change-me"))

    if unsafe_secret(SESSION_SECRET, 32):
        errors.append("SURI_SESSION_SECRET must be a random value of at least 32 characters")
    if not ADMIN_BOOTSTRAP_USERNAME:
        errors.append("SURI_ADMIN_USERNAME is required")
    if unsafe_secret(ADMIN_BOOTSTRAP_PASSWORD, 12):
        errors.append("SURI_ADMIN_PASSWORD must contain at least 12 characters")
    if not VIEWER_BOOTSTRAP_USERNAME:
        errors.append("SURI_VIEWER_USERNAME is required for the AFP view-only account")
    if unsafe_secret(VIEWER_BOOTSTRAP_PASSWORD, 12):
        errors.append("SURI_VIEWER_PASSWORD must contain at least 12 characters")
    if ADMIN_BOOTSTRAP_USERNAME == VIEWER_BOOTSTRAP_USERNAME:
        errors.append("Administrator and viewer usernames must differ")
    if ADMIN_BOOTSTRAP_PASSWORD == VIEWER_BOOTSTRAP_PASSWORD:
        errors.append("Administrator and viewer passwords must differ")
    if not CORS_ORIGINS or any(
        urlparse(origin).scheme != "https" or not urlparse(origin).hostname
        or urlparse(origin).hostname in {"localhost", "127.0.0.1"}
        or urlparse(origin).hostname.endswith("example.com")
        or urlparse(origin).path not in {"", "/"}
        for origin in CORS_ORIGINS
    ):
        errors.append("SURI_CORS_ORIGINS must contain real HTTPS deployment origins")
    if not TRUSTED_HOSTS or "*" in TRUSTED_HOSTS:
        errors.append("SURI_TRUSTED_HOSTS must explicitly list deployment hosts")
    if DB_ENGINE != "mariadb":
        errors.append("Production requires SURI_DATABASE_URL or MariaDB SURI_DB_* settings")
    from sqlalchemy.engine import make_url
    try:
        database_password = make_url(DATABASE_URL).password or ""
        if unsafe_secret(database_password, 16):
            errors.append("The database password must be a non-placeholder value of at least 16 characters")
    except Exception:
        errors.append("The database URL is invalid")
    if not MODEL_REQUIRED or not MODEL_WARMUP:
        errors.append("Production requires SURI_MODEL_REQUIRED=true and SURI_MODEL_WARMUP=true")
    if MODEL_PROFILE == "full-cleaned-20261023T022416Z":
        errors.append("The full-cleaned candidate profile is approved for local trial only")
    if errors:
        raise RuntimeError("Unsafe production configuration: " + "; ".join(errors))

RESEARCH_RETENTION_DAYS = max(1, _env_int("SURI_RESEARCH_RETENTION_DAYS", 30))
AUTO_MIGRATE = _env("SURI_AUTO_MIGRATE", "true" if APP_ENV != "production" else "false").lower() == "true"
TRAFFIC_LIMITS_ENABLED = _env("SURI_TRAFFIC_LIMITS", "true" if APP_ENV == "production" else "false").lower() == "true"
INFERENCE_TIMEOUT_SECONDS = max(1, _env_int("SURI_INFERENCE_TIMEOUT_SECONDS", 120))
