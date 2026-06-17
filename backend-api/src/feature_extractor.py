"""
feature_extractor.py — Stage 4 Track B: extract 7 scalar linguistic features.
"""
import re
import sys
import os
from typing import List
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


_ENGLISH_MARKERS = {
    "the", "is", "are", "was", "were", "have", "has", "had",
    "a", "an", "and", "or", "but", "not", "in", "on", "at",
}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", text.lower())


def code_switch_ratio(text: str) -> float:
    toks = _tokenize(text)
    if not toks:
        return 0.0
    # Count specific markers for both languages
    en = sum(1 for t in toks if t in _ENGLISH_MARKERS)
    fil = sum(1 for t in toks if t in config.FILIPINO_PARTICLES)
    total = len(toks)
    # Ratio is non-zero only if both languages are detected via markers
    if en > 0 and fil > 0:
        return (en + fil) / total
    return 0.0


def filipino_particle_count(text: str) -> int:
    toks = _tokenize(text)
    return sum(1 for t in toks if t in config.FILIPINO_PARTICLES)


def punctuation_intensity(text: str) -> float:
    if not text:
        return 0.0
    punc = len(re.findall(r"[!?.,:;]+", text))
    return punc / max(1, len(text))


def caps_ratio(text: str) -> float:
    if not text:
        return 0.0
    letters = re.findall(r"[A-Za-z]", text)
    if not letters:
        return 0.0
    caps = sum(1 for c in letters if c.isupper())
    return caps / len(letters)


def repeated_char_ratio(text: str) -> float:
    if not text:
        return 0.0
    repeats = len(re.findall(r"([a-zA-Z])\1{2,}", text))
    return repeats / max(1, len(text))


def emotional_word_count(text: str) -> int:
    toks = _tokenize(text)
    return sum(1 for t in toks if t in set(w.lower() for w in config.EMOTIONAL_WORDS))


def urgency_cue_count(text: str) -> int:
    low = text.lower()
    return sum(1 for p in config.URGENCY_PHRASES if p in low)


def extract_7_features(text: str) -> np.ndarray:
    a = code_switch_ratio(text)
    b = filipino_particle_count(text)
    c = punctuation_intensity(text)
    d = caps_ratio(text)
    e = repeated_char_ratio(text)
    f = emotional_word_count(text)
    g = urgency_cue_count(text)
    return np.array([a, b, c, d, e, f, g], dtype=float)


def batch_extract(texts: List[str]) -> np.ndarray:
    rows = [extract_7_features(t) for t in texts]
    return np.vstack(rows)
