"""The seven explicit linguistic/stylistic features defined in the revised paper."""

from __future__ import annotations

import re
from typing import List

import numpy as np

import config

FEATURE_NAMES = (
    "code_switching_ratio",
    "filipino_particle_frequency",
    "punctuation_intensity",
    "capitalization_ratio",
    "repeated_character_ratio",
    "emotional_language_frequency",
    "urgency_cue_frequency",
)

_WORD_RE = re.compile(r"\b[^\W_]+(?:['’-][^\W_]+)*\b", re.UNICODE)
_REPEATED_RE = re.compile(r"([^\W\d_])\1{2,}", re.UNICODE | re.IGNORECASE)
_FILIPINO = frozenset(word.casefold() for word in config.FILIPINO_PARTICLES)
_ENGLISH = frozenset(
    "a an and are as at be been but by can could did do does for from had has have he her "
    "hers him his how i if in into is it its may me more most my no not of on or our ours "
    "she should so than that the their theirs them then there these they this those through "
    "to too under up us was we were what when where which who why will with would you your yours"
    .split()
)
_EMOTIONAL = frozenset(word.casefold() for word in config.EMOTIONAL_WORDS)
_URGENCY = tuple(phrase.casefold() for phrase in config.URGENCY_PHRASES)


def _phrase_matches(text: str, phrases: tuple[str, ...]) -> int:
    return sum(len(re.findall(rf"(?<!\w){re.escape(phrase)}(?!\w)", text)) for phrase in phrases)


def extract_features(text: str) -> np.ndarray:
    """Compute features before destructive normalization; empty denominators return zero."""
    value = text if isinstance(text, str) else ""
    tokens = _WORD_RE.findall(value)
    lowered = [token.casefold() for token in tokens]
    token_count = len(tokens)
    filipino_count = sum(token in _FILIPINO for token in lowered)
    english_count = sum(token in _ENGLISH for token in lowered)
    character_count = len(value)
    alphabetic = [character for character in value if character.isalpha()]
    repeated_characters = sum(len(match.group(0)) for match in _REPEATED_RE.finditer(value))

    def ratio(numerator: int, denominator: int) -> float:
        return float(numerator / denominator) if denominator else 0.0

    return np.asarray(
        [
            ratio(min(filipino_count, english_count), token_count),
            ratio(filipino_count, token_count),
            ratio(sum(character in "!?" for character in value), character_count),
            ratio(sum(character.isupper() for character in alphabetic), len(alphabetic)),
            ratio(repeated_characters, character_count),
            ratio(sum(token in _EMOTIONAL for token in lowered), token_count),
            ratio(_phrase_matches(value.casefold(), _URGENCY), token_count),
        ],
        dtype=np.float64,
    )


def extract_7_features(text: str) -> np.ndarray:
    return extract_features(text)


def batch_extract(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, len(FEATURE_NAMES)), dtype=np.float64)
    return np.vstack([extract_features(text) for text in texts])
