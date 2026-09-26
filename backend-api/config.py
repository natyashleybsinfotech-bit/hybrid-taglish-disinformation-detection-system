"""Environment-backed configuration for the SuriPH working prototype."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
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
DB_HOST = _env("SURI_DB_HOST", "127.0.0.1")
DB_PORT = _env_int("SURI_DB_PORT", 3306)
DB_USER = _env("SURI_DB_USER")
DB_PASSWORD = os.getenv("SURI_DB_PASSWORD", "")
DB_NAME = _env("SURI_DB_NAME", "suriph")
DB_CONNECT_TIMEOUT = _env_int("SURI_DB_CONNECT_TIMEOUT", 2)
ADMIN_BOOTSTRAP_USERNAME = _env("SURI_ADMIN_USERNAME")
ADMIN_BOOTSTRAP_PASSWORD = os.getenv("SURI_ADMIN_PASSWORD", "")
SESSION_SECRET = os.getenv("SURI_SESSION_SECRET", "")
SESSION_HOURS = _env_int("SURI_SESSION_HOURS", 8)
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
MODEL_STATUS = "mock-prototype"
DISCLAIMER = (
    "DISCLAIMER: This result is an assistive screening signal, not proof that a claim is true or false. "
    "Please read the cited sources, check the posting date and full context, and consult professional fact-checkers when needed."
)

# Legacy constants remain import-compatible, but Sprint 1 does not load the model.
MODEL_PATH = BASE_DIR / "models" / "hybrid_model.pkl"
RAW_DATA_PATH = BASE_DIR / "data" / "raw" / "corpus.csv"
PROCESSED_DATA_PATH = BASE_DIR / "data" / "processed" / "features.npz"
CLEAN_CSV_PATH = BASE_DIR / "data" / "processed" / "clean.csv"
DISTILBERT_SAVE_PATH = BASE_DIR / "models" / "distilbert_embedder"
DISTILBERT_MODEL_NAME = "distilbert-base-multilingual-cased"
MAX_SEQ_LENGTH = 128
BATCH_SIZE = 32
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15
RANDOM_SEED = 42
CLASSIFICATION_THRESHOLD = 0.50
FILIPINO_PARTICLES = [
    "ba", "kasi", "naman", "nga", "pa", "na", "daw", "raw", "lang", "po",
    "ate", "kuya", "pala", "eh", "talaga", "sobra", "grabe", "ay", "hay",
    "nako", "sana", "kung", "bakit", "hindi", "pero", "at", "ng", "ang",
    "mga", "yung", "ito", "iyon", "siya", "kami", "tayo", "nila", "ko",
    "mo", "niya", "natin", "namin", "ninyo", "din", "rin", "man", "dito",
    "diyan", "doon", "ano", "sino", "saan", "kailan", "paano", "gaano",
    "oo", "opo", "huwag", "wag",
]
URGENCY_PHRASES = [
    "share agad", "now na", "bago matanggal", "breaking", "grabe ito",
    "pakishare", "i-share na", "urgent", "bilisan", "asap", "huwag palampasin",
]
EMOTIONAL_WORDS = [
    "galit", "takot", "kawawa", "nakakalungkot", "nakakatakot", "nakakainis",
    "nakakagulat", "nakakaawa", "nakakatuwa", "nakakaloka", "baliw", "gago",
    "mahal", "masakit", "nasaktan", "iyak", "luha", "saya", "masaya",
    "malungkot", "nagagalit", "natatakot", "naiinis", "nagulat", "nagulantang",
]
