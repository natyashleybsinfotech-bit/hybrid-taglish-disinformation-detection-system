"""Evidence-first assessment without a trained claim classifier."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

try:
    from .fact_check import search_fact_checks
    from .retrieval import retrieve_related_sources
except ImportError:
    from fact_check import search_fact_checks
    from retrieval import retrieve_related_sources


STRONG_FACT_CHECK_MATCH = 0.70
MINIMUM_MATCHED_TERMS = 3


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _strong_fact_checks(matches: list[dict]) -> list[dict]:
    return [
        match for match in matches
        if float(match.get("match_strength") or 0) >= STRONG_FACT_CHECK_MATCH
        and int(match.get("matched_term_count") or 0) >= MINIMUM_MATCHED_TERMS
        and str(match.get("rating") or "").strip()
        and str(match.get("url") or "").strip()
    ]


def assess_evidence(text: str, *, requested: bool, excluded_domain: str | None = None) -> dict:
    """Return cited evidence states; never fabricate or infer a binary truth label."""
    analyzed_text = normalize_text(text)
    if not analyzed_text:
        raise ValueError("No usable text was provided for assessment.")
    if not requested:
        return {
            "assessment_status": "unresolved",
            "assessment_label": "Evidence lookup not requested",
            "assessment_basis": "No external evidence was requested, so SuriPH did not determine a verdict.",
            "decision_source": "insufficient_evidence",
            "retrieval_status": "not_requested",
            "related_sources": [],
            "fact_check_status": "not_requested",
            "fact_check_matches": [],
        }

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="suriph-evidence") as executor:
        retrieval_future = executor.submit(
            retrieve_related_sources, analyzed_text, excluded_domain=excluded_domain
        )
        fact_check_future = executor.submit(search_fact_checks, analyzed_text)
        try:
            retrieval = retrieval_future.result()
        except Exception:
            retrieval = {"retrieval_status": "unavailable", "related_sources": []}
        try:
            fact_checks = fact_check_future.result()
        except Exception:
            fact_checks = {"status": "unavailable", "matches": [], "signal": None}

    strong_matches = _strong_fact_checks(fact_checks.get("matches", []))
    sources = retrieval.get("related_sources", [])
    if strong_matches:
        first = strong_matches[0]
        publisher = first.get("publisher") or urlparse(first["url"]).netloc or "Fact-check publisher"
        rating = first["rating"]
        return {
            "assessment_status": "published_fact_check",
            "assessment_label": f"Published fact-check: {rating}",
            "assessment_basis": (
                f"{publisher} published a closely matching ClaimReview rating. "
                "This is the publisher's finding, not a SuriPH model prediction."
            ),
            "decision_source": "published_fact_check",
            "retrieval_status": retrieval.get("retrieval_status", "unavailable"),
            "related_sources": sources,
            "fact_check_status": "available",
            "fact_check_matches": strong_matches,
        }
    if sources:
        count = len(sources)
        return {
            "assessment_status": "related_coverage",
            "assessment_label": "Related coverage found",
            "assessment_basis": (
                f"{count} related article{'s' if count != 1 else ''} from approved publishers were found. "
                "They have not been verified as proving or disproving every detail of the post."
            ),
            "decision_source": "related_sources",
            "retrieval_status": retrieval.get("retrieval_status", "available"),
            "related_sources": sources,
            "fact_check_status": fact_checks.get("status", "no_results"),
            "fact_check_matches": [],
        }
    unavailable = (
        retrieval.get("retrieval_status") in {"unavailable", "unavailable_not_configured", "disabled"}
        and fact_checks.get("status") in {"unavailable", "unavailable_not_configured", "disabled"}
    )
    return {
        "assessment_status": "providers_unavailable" if unavailable else "unresolved",
        "assessment_label": "Evidence providers unavailable" if unavailable else "Unresolved",
        "assessment_basis": (
            "Neither configured evidence provider completed the lookup. No verdict was produced."
            if unavailable else
            "No closely matching published fact-check or related approved-source coverage was found. "
            "Absence of results is not evidence that the post is true or false."
        ),
        "decision_source": "insufficient_evidence",
        "retrieval_status": retrieval.get("retrieval_status", "unavailable"),
        "related_sources": [],
        "fact_check_status": fact_checks.get("status", "unavailable"),
        "fact_check_matches": [],
    }


def evidence_health(*, serper_configured: bool, fact_check_configured: bool) -> dict:
    configured = []
    if serper_configured:
        configured.append("serper")
    if fact_check_configured:
        configured.append("google_fact_check")
    return {
        "status": "ready" if configured else "unavailable_not_configured",
        "ready": bool(configured),
        "mode": "evidence_only",
        "classifier_loaded": False,
        "classifier": None,
        "configured_providers": configured,
        "outcomes": ["published_fact_check", "related_coverage", "unresolved"],
        "binary_verdict_without_evidence": False,
    }
