"""Independent server-side Serper.dev retrieval for related-source context."""

from __future__ import annotations

import json
import re
from urllib import error, request
from urllib.parse import urlparse

import config


def _source_name(item: dict) -> str:
    link = str(item.get("link", ""))
    return str(item.get("source") or urlparse(link).netloc or "").removeprefix("www.")


SOCIAL_DOMAINS = {
    "facebook.com", "fb.com", "instagram.com", "tiktok.com", "x.com", "twitter.com",
    "youtube.com", "youtu.be", "reddit.com", "redd.it", "threads.net", "telegram.org",
}
TRUSTED_DOMAIN_SUFFIXES = {
    "reuters.com", "apnews.com", "bbc.com", "npr.org", "who.int", "un.org", "snopes.com",
    "politifact.com", "afp.com", "factcheck.afp.com", "inquirer.net", "rappler.com",
    "gmanetwork.com", "abs-cbn.com", "philstar.com", "pna.gov.ph", "officialgazette.gov.ph",
    "gov.ph", "doh.gov.ph", "comelec.gov.ph", "edu.ph", "verafiles.org",
    "mb.com.ph", "manilatimes.net", "bworldonline.com", "pia.gov.ph",
}


def _search_query(query: str) -> str:
    """Keep the claim searchable without Facebook UI text or social results."""
    cleaned = re.sub(r"https?://\S+|www\.\S+", " ", query, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(?:read|see)\s+(?:more|less)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-|\"")[:500]
    exclusions = " -site:facebook.com -site:tiktok.com -site:x.com -site:youtube.com -site:reddit.com"
    return f"{cleaned}{exclusions}".strip()


def _is_blocked_domain(host: str, excluded_domain: str | None) -> bool:
    host = host.casefold().removeprefix("www.")
    excluded = (excluded_domain or "").casefold().removeprefix("www.")
    return any(host == domain or host.endswith(f".{domain}") for domain in SOCIAL_DOMAINS) or bool(excluded and (host == excluded or host.endswith(f".{excluded}")))


def _is_trusted_domain(host: str) -> bool:
    host = host.casefold().removeprefix("www.")
    return any(host == domain or host.endswith(f".{domain}") for domain in TRUSTED_DOMAIN_SUFFIXES)


def retrieve_related_sources(query: str, excluded_domain: str | None = None) -> dict:
    if not config.SERPER_ENABLED:
        return {"retrieval_status": "disabled", "related_sources": []}
    if not config.SERPER_API_KEY:
        return {"retrieval_status": "unavailable_not_configured", "related_sources": []}
    # Fetch a wider candidate set in the same Serper request, then keep only a
    # small, diverse set of approved sources for the user.
    # Ten is accepted by all Serper search plans; larger custom counts can be
    # rejected with HTTP 400 on restricted accounts.
    candidate_count = 10
    payload = json.dumps({"q": _search_query(query), "num": candidate_count, "gl": "ph", "hl": "en"}).encode("utf-8")
    req = request.Request(
        "https://google.serper.dev/search",
        data=payload,
        method="POST",
        headers={"X-API-KEY": config.SERPER_API_KEY, "Content-Type": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=config.SERPER_TIMEOUT_SECONDS) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, TimeoutError, json.JSONDecodeError):
        return {"retrieval_status": "unavailable", "related_sources": []}
    sources = []
    seen_hosts: set[str] = set()
    for item in body.get("organic", []):
        url = str(item.get("link", "")).strip()
        title = str(item.get("title", "")).strip()
        host = urlparse(url).netloc
        normalized_host = host.casefold().removeprefix("www.")
        if url and title and normalized_host not in seen_hosts and _is_trusted_domain(host) and not _is_blocked_domain(host, excluded_domain):
            sources.append({
                "title": title,
                "url": url,
                "snippet": str(item.get("snippet", "")).strip(),
                "source": _source_name(item),
            })
            seen_hosts.add(normalized_host)
            if len(sources) == config.SERPER_MAX_RESULTS:
                break
    return {
        "retrieval_status": "available" if sources else "no_results",
        "related_sources": sources,
    }
