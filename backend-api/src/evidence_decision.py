"""Evidence-assisted binary decision rules layered over the pinned model prediction."""

from __future__ import annotations

import re
from urllib.parse import urlparse


STRONG_FACT_CHECK_MATCH = 0.70
MINIMUM_MATCHED_TERMS = 3
SUPPORTING_RATINGS = ("true", "correct", "accurate", "verified", "mostly true")
DEBUNKING_RATINGS = (
    "false", "misleading", "fake", "incorrect", "altered", "manipulated",
    "fabricated", "no evidence", "scam", "pants on fire", "peke", "hindi totoo",
)
DEBUNKING_SOURCE_PATTERNS = (
    r"\bfact[ -]?check\b", r"\bdebunk", r"\bfalse\b", r"\bfake\b",
    r"\bmisleading\b", r"\bhoax\b", r"\bnot true\b", r"\bno evidence\b",
    r"\bden(?:y|ies|ied)\b", r"\brefut", r"\bfabricat", r"\bmanipulat",
    r"\bpeke\b", r"\bhindi totoo\b", r"\bwalang basehan\b",
)
PRIMARY_SOURCE_SUFFIXES = ("gov.ph", "officialgazette.gov.ph", "who.int", "un.org")


def _rating_kind(rating: str) -> str | None:
    normalized = re.sub(r"\s+", " ", (rating or "").casefold()).strip()
    if any(term in normalized for term in DEBUNKING_RATINGS):
        return "debunk"
    if any(term == normalized or normalized.startswith(f"{term} ") for term in SUPPORTING_RATINGS):
        return "support"
    return None


def _strong_matches(matches: list[dict]) -> list[dict]:
    return [
        item for item in matches
        if float(item.get("match_strength") or 0) >= STRONG_FACT_CHECK_MATCH
        and int(item.get("matched_term_count") or 0) >= MINIMUM_MATCHED_TERMS
        and item.get("url") and _rating_kind(str(item.get("rating") or ""))
    ]


def _looks_debunking(source: dict) -> bool:
    text = f"{source.get('title', '')} {source.get('snippet', '')}".casefold()
    return any(re.search(pattern, text) for pattern in DEBUNKING_SOURCE_PATTERNS)


def _is_primary_source(source: dict) -> bool:
    host = (urlparse(str(source.get("url") or "")).hostname or str(source.get("source") or "")).casefold().removeprefix("www.")
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in PRIMARY_SOURCE_SUFFIXES)


def apply_evidence(model_prediction: dict, related_sources: list[dict], fact_check_matches: list[dict]) -> dict:
    """Return exactly one of the two product labels, with an attributable basis."""
    strong = _strong_matches(fact_check_matches)
    debunk = next((item for item in strong if _rating_kind(str(item.get("rating"))) == "debunk"), None)
    support = next((item for item in strong if _rating_kind(str(item.get("rating"))) == "support"), None)

    if debunk:
        publisher = debunk.get("publisher") or "A published fact-check"
        return {
            "internal_label": "Misleading", "public_label": "Potentially Misleading",
            "decision_source": "published_fact_check",
            "decision_basis": f"{publisher} published a closely matching rating: {debunk['rating']}.",
            "supporting_source_count": 0, "strong_fact_check_matches": strong,
        }
    if support:
        publisher = support.get("publisher") or "A published fact-check"
        return {
            "internal_label": "Non-Misleading", "public_label": "No Misleading Information Detected",
            "decision_source": "published_fact_check",
            "decision_basis": f"{publisher} published a closely matching rating: {support['rating']}.",
            "supporting_source_count": 0, "strong_fact_check_matches": strong,
        }

    supporting = [source for source in related_sources if not _looks_debunking(source)]
    official = next((source for source in supporting if _is_primary_source(source)), None)
    if official:
        publisher = official.get("source") or urlparse(str(official.get("url"))).hostname or "an official source"
        return {
            "internal_label": "Non-Misleading", "public_label": "No Misleading Information Detected",
            "decision_source": "official_primary_source",
            "decision_basis": f"The core claim is corroborated by a relevant official primary source: {publisher}.",
            "supporting_source_count": 1, "strong_fact_check_matches": strong,
        }
    if len(supporting) >= 2:
        return {
            "internal_label": "Non-Misleading", "public_label": "No Misleading Information Detected",
            "decision_source": "corroborated_sources",
            "decision_basis": f"The core claim is corroborated by {len(supporting)} relevant reports from independent approved publishers.",
            "supporting_source_count": len(supporting), "strong_fact_check_matches": strong,
        }

    return {
        "internal_label": model_prediction["internal_label"],
        "public_label": model_prediction["public_label"],
        "decision_source": "screening_model",
        "decision_basis": "No decisive evidence override was available; the displayed label follows the pinned model_4 prediction.",
        "supporting_source_count": len(supporting), "strong_fact_check_matches": strong,
    }
