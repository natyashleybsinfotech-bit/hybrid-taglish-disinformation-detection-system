"""
config.py — Single source of truth for all project constants.
Every other module imports paths, model names, thresholds, and feature lists from here.
"""

import os

# ── Project root (this file lives at taglish-detector/config.py) ──────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Data paths ────────────────────────────────────────────────────────────────
RAW_DATA_PATH = os.path.join(BASE_DIR, "data", "raw", "corpus.csv")
PROCESSED_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "features.npz")
CLEAN_CSV_PATH = os.path.join(BASE_DIR, "data", "processed", "clean.csv")

# ── Model paths ───────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(BASE_DIR, "models", "hybrid_model.pkl")
DISTILBERT_SAVE_PATH = os.path.join(BASE_DIR, "models", "distilbert_embedder")

# ── DistilBERT settings ──────────────────────────────────────────────────────
DISTILBERT_MODEL_NAME = "distilbert-base-multilingual-cased"
MAX_SEQ_LENGTH = 128
BATCH_SIZE = 32

# ── Train / Val / Test split ─────────────────────────────────────────────────
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15
RANDOM_SEED = 42

# ── Classification ────────────────────────────────────────────────────────────
CLASSIFICATION_THRESHOLD = 0.50

# ── Filipino particles (used by taglish_filter and feature_extractor) ────────
FILIPINO_PARTICLES = [
    "ba", "kasi", "naman", "nga", "pa", "na", "daw", "raw", "lang", "po",
    "ate", "kuya", "pala", "eh", "talaga", "sobra", "grabe", "ay", "hay",
    "nako", "sana", "kung", "bakit", "hindi", "pero", "at", "ng", "ang",
    "mga", "yung", "ito", "iyon", "siya", "kami", "tayo", "nila",
    "ko", "mo", "niya", "natin", "namin", "ninyo",
    "din", "rin", "man", "dito", "diyan", "doon",
    "ano", "sino", "saan", "kailan", "paano", "gaano",
    "oo", "opo", "hindi", "huwag", "wag",
]

# ── Urgency phrases (substring match, case-insensitive) ──────────────────────
URGENCY_PHRASES = [
    "share agad", "now na", "bago matanggal", "breaking", "grabe ito",
    "pakishare", "i-share na", "urgent", "bilisan", "asap",
    "huwag palampasin", "pinakamahalagang", "tandaan ninyo",
    "hindi dapat malaman", "itago", "huwag tanggalin",
]

# ── Emotional words (token match, case-insensitive) ──────────────────────────
EMOTIONAL_WORDS = [
    "galit", "takot", "kawawa", "nakakalungkot", "nakakatakot",
    "nakakainis", "nakakagulat", "nakakaawa", "nakakatuwa", "nakakaloka",
    "baliw", "gago", "putangina", "hayop", "mahal", "masakit",
    "nasaktan", "iyak", "luha", "saya", "masaya", "malungkot",
    "galit na galit", "nagagalit", "natatakot", "naiinis",
    "nagulat", "nagulantang",
]
