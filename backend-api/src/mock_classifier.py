"""Deterministic temporary classifier used only by the Sprint 1 prototype."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass

import config


@dataclass(frozen=True)
class MockPrediction:
    internal_label: str
    public_label: str
    temporary_score: float
    model_status: str = config.MODEL_STATUS

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def classify(text: str) -> MockPrediction:
    """Return a repeatable placeholder result derived from the normalized text hash."""
    normalized = normalize_text(text)
    if not normalized:
        raise ValueError("Text is required for screening.")
    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    misleading = bool(digest[0] & 1)
    score = round(0.55 + (int.from_bytes(digest[1:3], "big") / 65535) * 0.39, 4)
    return MockPrediction(
        internal_label="Misleading" if misleading else "Non-Misleading",
        public_label=(
            "Potentially Misleading"
            if misleading
            else "No Misleading Information Detected"
        ),
        temporary_score=score,
    )
