"""Google Fact Check Tools Claim Search integration."""

from __future__ import annotations

import json
import re
from urllib import error, parse, request

import config


def _tokens(value: str) -> set[str]:
    ignored = {"the", "and", "for", "that", "this", "with", "from", "ang", "mga", "sa", "ng", "na"}
    return {word for word in re.findall(r"[a-zA-Z]{3,}", value.casefold()) if word not in ignored}


def _similarity(query: str, claim: str) -> float:
    query_tokens, claim_tokens = _tokens(query), _tokens(claim)
    if not query_tokens or not claim_tokens:
        return 0.0
    return round(len(query_tokens & claim_tokens) / min(len(query_tokens), len(claim_tokens)), 3)


def _evidence_signal(matches: list[dict]) -> dict | None:
    """Derive a conservative verdict signal from closely matching ClaimReviews."""
    false_terms = {
        "false", "misleading", "incorrect", "fake", "fabricated", "scam",
        "altered", "out of context", "not true", "pants on fire",
    }
    true_terms = {"true", "correct", "accurate", "verified", "legitimate"}
    supported: list[tuple[str, dict]] = []

    for match in matches:
        if float(match.get("match_strength", 0)) < 0.5:
            continue
        rating = str(match.get("rating", "")).casefold()
        if any(term in rating for term in false_terms):
            supported.append(("Misleading", match))
        elif any(term in rating for term in true_terms):
            supported.append(("Non-Misleading", match))

    if not supported:
        return None

    misleading_count = sum(label == "Misleading" for label, _ in supported)
    non_misleading_count = len(supported) - misleading_count
    if misleading_count == non_misleading_count:
        return None

    chosen_label = "Misleading" if misleading_count > non_misleading_count else "Non-Misleading"
    best_match = max(
        (match for label, match in supported if label == chosen_label),
        key=lambda item: float(item.get("match_strength", 0)),
    )
    strength = float(best_match.get("match_strength", 0))
    return {
        "internal_label": chosen_label,
        "public_label": "Potentially Misleading" if chosen_label == "Misleading" else "No Misleading Information Detected",
        "confidence": round(min(0.95, 0.75 + strength * 0.2), 4),
        "basis": f"A closely matching published fact-check rated the claim as: {best_match.get('rating', 'not stated')}",
        "source_url": best_match.get("url", ""),
    }


def search_fact_checks(query: str) -> dict:
    if not config.GOOGLE_FACT_CHECK_ENABLED:
        return {"status": "disabled", "matches": [], "signal": None}
    if not config.GOOGLE_FACT_CHECK_API_KEY:
        return {"status": "unavailable_not_configured", "matches": [], "signal": None}

    params = parse.urlencode({
        "query": query[:500],
        "pageSize": config.GOOGLE_FACT_CHECK_MAX_RESULTS,
        "key": config.GOOGLE_FACT_CHECK_API_KEY,
    })
    endpoint = f"https://factchecktools.googleapis.com/v1alpha1/claims:search?{params}"
    try:
        with request.urlopen(endpoint, timeout=config.GOOGLE_FACT_CHECK_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
        return {"status": "unavailable", "matches": [], "signal": None}

    matches = []
    seen_urls: set[str] = set()
    for claim in body.get("claims", []):
        claim_text = str(claim.get("text", "")).strip()
        similarity = _similarity(query, claim_text)
        for review in claim.get("claimReview", []):
            url = str(review.get("url", "")).strip()
            if not url or url in seen_urls:
                continue
            publisher = review.get("publisher") or {}
            matches.append({
                "claim": claim_text,
                "claimant": str(claim.get("claimant", "")).strip(),
                "claim_date": str(claim.get("claimDate", "")).strip(),
                "publisher": str(publisher.get("name") or publisher.get("site") or "Fact-check publisher").strip(),
                "publisher_site": str(publisher.get("site", "")).strip(),
                "title": str(review.get("title") or claim_text or "Fact-check review").strip(),
                "url": url,
                "rating": str(review.get("textualRating") or "Rating not provided").strip(),
                "review_date": str(review.get("reviewDate", "")).strip(),
                "language": str(review.get("languageCode", "")).strip(),
                "match_strength": similarity,
            })
            seen_urls.add(url)
            if len(matches) == config.GOOGLE_FACT_CHECK_MAX_RESULTS:
                break
        if len(matches) == config.GOOGLE_FACT_CHECK_MAX_RESULTS:
            break
    return {
        "status": "available" if matches else "no_results",
        "matches": matches,
        "signal": _evidence_signal(matches),
    }
