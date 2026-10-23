"""Google Fact Check Tools Claim Search integration."""

from __future__ import annotations

import json
import re
from urllib import error, parse, request

import config
try:
    from .provider_http import open_provider, read_json, safe_link
except ImportError:
    from provider_http import open_provider, read_json, safe_link


def _tokens(value: str) -> set[str]:
    ignored = {"the", "and", "for", "that", "this", "with", "from", "ang", "mga", "sa", "ng", "na"}
    return {word for word in re.findall(r"[a-zA-Z]{3,}", value.casefold()) if word not in ignored}


def _similarity(query: str, claim: str) -> tuple[float, int]:
    query_tokens, claim_tokens = _tokens(query), _tokens(claim)
    if not query_tokens or not claim_tokens:
        return 0.0, 0
    matched = len(query_tokens & claim_tokens)
    return round(matched / min(len(query_tokens), len(claim_tokens)), 3), matched


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
        with open_provider(endpoint, timeout=config.GOOGLE_FACT_CHECK_TIMEOUT_SECONDS) as response:
            body = read_json(response)
    except (error.HTTPError, error.URLError, TimeoutError, ValueError):
        return {"status": "unavailable", "matches": [], "signal": None}

    matches = []
    seen_urls: set[str] = set()
    for claim in body.get("claims", []):
        claim_text = str(claim.get("text", "")).strip()
        similarity, matched_terms = _similarity(query, claim_text)
        for review in claim.get("claimReview", []):
            url = str(review.get("url", "")).strip()
            if not safe_link(url) or url in seen_urls:
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
                "matched_term_count": matched_terms,
            })
            seen_urls.add(url)
            if len(matches) == config.GOOGLE_FACT_CHECK_MAX_RESULTS:
                break
        if len(matches) == config.GOOGLE_FACT_CHECK_MAX_RESULTS:
            break
    return {
        "status": "available" if matches else "no_results",
        "matches": matches,
        "signal": None,
    }
