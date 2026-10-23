"""Independent server-side Serper.dev retrieval for related-source context."""

from __future__ import annotations

import json
import re
import unicodedata
from urllib import error, request
from urllib.parse import urlparse

import config
try:
    from .provider_http import open_provider, read_json, safe_link
except ImportError:
    from provider_http import open_provider, read_json, safe_link


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
FOCUSED_NEWS_DOMAINS = (
    "gmanetwork.com", "abs-cbn.com", "inquirer.net", "rappler.com", "philstar.com",
    "mb.com.ph", "pna.gov.ph", "pia.gov.ph", "verafiles.org", "manilatimes.net",
)

# Terms that are frequent in prose, social-post chrome, or dates do not establish
# that a search result discusses the same event.  Keep this deliberately small and
# language-neutral enough for English/Filipino/Taglish news text.
RELEVANCE_STOP_WORDS = {
    "about", "after", "again", "against", "also", "ang", "ano", "at", "ay",
    "before", "being", "but", "city", "courtesy", "dahil", "daw", "from",
    "gabi", "had", "has", "have", "here", "hindi", "ito", "isang", "kanila",
    "kanilang", "kanina", "kasi", "kaya", "kung", "lang", "latest", "mga",
    "abs", "bulletin", "cbn", "gma", "inquirer", "more", "mula", "naman",
    "nang", "news", "ng", "nga", "ngayon", "ni",
    "nila", "noong", "para", "pero", "post", "read", "report", "said", "sa",
    "philstar", "rappler", "see", "share", "si", "sila", "source", "that", "the", "their", "there",
    "this", "through", "today", "umano", "update", "upon", "via", "was", "were",
    "what", "when", "where", "which", "while", "who", "with", "yung",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "jan", "feb", "mar", "apr",
    "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
}
CANONICAL_TERMS = {
    "suspek": "suspect", "suspects": "suspect",
    "naaresto": "arrest", "inaresto": "arrest", "arestado": "arrest",
    "arrested": "arrest", "arrests": "arrest",
    "murder": "kill", "murdered": "kill", "killed": "kill", "killing": "kill",
    "patay": "kill", "pinatay": "kill", "pinaslang": "kill", "napatay": "kill",
    "shooting": "shoot", "shot": "shoot", "binaril": "shoot", "pamamaril": "shoot",
    "barilan": "shoot", "pulis": "police",
    "lindol": "earthquake", "sunog": "fire", "baha": "flood", "bagyo": "typhoon",
    "eleksyon": "election", "halalan": "election", "boto": "vote",
}

PERSON_CONNECTORS = {"da", "de", "del", "dela", "dello", "delos", "dos", "la", "las", "los", "van", "von"}
PERSON_TITLES = {
    "atty", "capt", "chief", "col", "cong", "dr", "father", "gen", "gov",
    "judge", "kap", "mayor", "mr", "mrs", "ms", "nanay", "pastor", "pres",
    "pssg", "sen", "sgt", "tatay",
}
EPISODIC_MARKERS = {
    "episode", "episodes", "teleserye", "trailer", "teaser", "recap",
    "kapamilya", "character", "season", "finale",
}


def _canonical_term(term: str) -> str:
    return CANONICAL_TERMS.get(term, term)


def _informative_terms(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    terms = set(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))
    return {
        _canonical_term(term) for term in terms
        if len(term) >= 3 and not term.isdigit() and term not in RELEVANCE_STOP_WORDS
    }


def _ordered_informative_terms(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    ordered = []
    for term in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE):
        canonical = _canonical_term(term)
        if len(term) < 3 or term.isdigit() or term in RELEVANCE_STOP_WORDS or canonical in ordered:
            continue
        ordered.append(canonical)
    return ordered


def _person_entity_anchors(text: str) -> set[tuple[str, ...]]:
    """Extract conservative full-name anchors without depending on an online NER model."""
    tokens = re.findall(r"[^\W\d_]+(?:[-'][^\W\d_]+)*|[.:!?;,]", unicodedata.normalize("NFKC", text), flags=re.UNICODE)
    anchors: set[tuple[str, ...]] = set()
    group: list[str] = []

    def finish():
        nonlocal group
        if not group:
            return
        normalized = [token.casefold().strip(".") for token in group]
        had_title = bool(normalized and normalized[0] in PERSON_TITLES)
        while normalized and normalized[0] in PERSON_TITLES:
            normalized.pop(0)
        name_words = [token for token in normalized if token not in PERSON_CONNECTORS]
        has_connector = any(token in PERSON_CONNECTORS for token in normalized)
        if len(name_words) >= 2 and len(normalized) >= 3 and (had_title or has_connector):
            anchors.add(tuple(normalized))
        group = []

    for token in tokens:
        folded = token.casefold().strip(".")
        is_name_word = token[:1].isupper() and token.replace("-", "").replace("'", "").isalpha()
        if is_name_word or (group and folded in PERSON_CONNECTORS):
            group.append(token)
            if len(group) > 6:
                finish()
        else:
            finish()
    finish()
    return anchors


def _contains_episodic_markers(text: str) -> bool:
    terms = set(re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold(), flags=re.UNICODE))
    return bool(terms & EPISODIC_MARKERS) or bool(re.search(r"\b(?:ep|episode)\s*\d+\b", text, flags=re.IGNORECASE))


def _entity_and_content_alignment(query: str, item: dict) -> bool:
    candidate = " ".join((str(item.get("title", "")), str(item.get("snippet", "")), str(item.get("link", ""))))
    if _contains_episodic_markers(candidate) and not _contains_episodic_markers(query):
        return False
    query_people = _person_entity_anchors(query)
    if not query_people:
        return True
    candidate_people = _person_entity_anchors(candidate)
    return bool(query_people & candidate_people)


def _term_matches(query_term: str, candidate_term: str) -> bool:
    if query_term == candidate_term:
        return True
    # Accommodate common inflections such as impeach/impeachment without broad
    # fuzzy matching that could admit an unrelated article.
    return min(len(query_term), len(candidate_term)) >= 7 and query_term[:7] == candidate_term[:7]


def _relevance(item: dict, query_terms: set[str]) -> tuple[int, int, int]:
    title_terms = _informative_terms(str(item.get("title", "")))
    snippet_terms = _informative_terms(str(item.get("snippet", "")))
    title_matches = {
        query_term for query_term in query_terms
        if any(_term_matches(query_term, candidate_term) for candidate_term in title_terms)
    }
    all_candidate_terms = title_terms | snippet_terms
    all_matches = {
        query_term for query_term in query_terms
        if any(_term_matches(query_term, candidate_term) for candidate_term in all_candidate_terms)
    }
    # Title matches carry more weight, but at least three distinct informative
    # terms are required for normal post-sized queries.  A credible domain alone
    # is never enough to display a link as related.
    return len(all_matches), len(title_matches), len(all_matches) + (2 * len(title_matches))


def _is_relevant(item: dict, query_terms: set[str], query: str = "") -> tuple[bool, int]:
    matched_terms, title_matches, score = _relevance(item, query_terms)
    required_matches = len(query_terms) if len(query_terms) <= 2 else 2 if len(query_terms) <= 5 else 3
    title_required = 2 if len(query_terms) > 5 else 1 if len(query_terms) >= 3 else 0
    aligned = _entity_and_content_alignment(query, item) if query else True
    return matched_terms >= required_matches and title_matches >= title_required and aligned, score


def _search_query(query: str) -> str:
    """Keep the claim searchable without embedded URLs or social results."""
    cleaned = re.sub(r"https?://\S+|www\.\S+", " ", query, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-|\"")[:500]
    exclusions = " -site:facebook.com -site:tiktok.com -site:x.com -site:youtube.com -site:reddit.com"
    return f"{cleaned}{exclusions}".strip()


def _focused_search_query(query: str) -> str:
    """Retry with concise event terms constrained to approved Philippine publishers."""
    terms = " ".join(_ordered_informative_terms(query)[:18])
    domains = " OR ".join(f"site:{domain}" for domain in FOCUSED_NEWS_DOMAINS)
    return f"{terms} ({domains})".strip()


def _is_blocked_domain(host: str, excluded_domain: str | None) -> bool:
    host = host.casefold().removeprefix("www.")
    excluded = (excluded_domain or "").casefold().removeprefix("www.")
    return any(host == domain or host.endswith(f".{domain}") for domain in SOCIAL_DOMAINS) or bool(excluded and (host == excluded or host.endswith(f".{excluded}")))


def _is_trusted_domain(host: str) -> bool:
    host = host.casefold().removeprefix("www.")
    return any(host == domain or host.endswith(f".{domain}") for domain in TRUSTED_DOMAIN_SUFFIXES)


def _serper_search(search_query: str) -> dict | None:
    payload = json.dumps({"q": search_query, "num": 10, "gl": "ph", "hl": "en"}).encode("utf-8")
    req = request.Request(
        "https://google.serper.dev/search",
        data=payload,
        method="POST",
        headers={"X-API-KEY": config.SERPER_API_KEY, "Content-Type": "application/json"},
    )
    try:
        with open_provider(req, timeout=config.SERPER_TIMEOUT_SECONDS) as response:
            return read_json(response)
    except (error.HTTPError, error.URLError, TimeoutError, ValueError):
        return None


def _relevant_sources(body: dict, query_terms: set[str], query: str, excluded_domain: str | None) -> list[tuple[int, dict]]:
    candidates = []
    seen_hosts: set[str] = set()
    for item in body.get("organic", []):
        url = str(item.get("link", "")).strip()
        title = str(item.get("title", "")).strip()
        host = urlparse(url).netloc
        normalized_host = host.casefold().removeprefix("www.")
        relevant, relevance_score = _is_relevant(item, query_terms, query)
        if safe_link(url) and title and relevant and normalized_host not in seen_hosts and _is_trusted_domain(host) and not _is_blocked_domain(host, excluded_domain):
            candidates.append((relevance_score, {
                "title": title,
                "url": url,
                "snippet": str(item.get("snippet", "")).strip(),
                "source": _source_name(item),
                "date": item.get("date") or None,
                "kind": "search_result",
            }))
            seen_hosts.add(normalized_host)
    return candidates


def retrieve_related_sources(query: str, excluded_domain: str | None = None) -> dict:
    if not config.SERPER_ENABLED:
        return {"retrieval_status": "disabled", "related_sources": []}
    if not config.SERPER_API_KEY:
        return {"retrieval_status": "unavailable_not_configured", "related_sources": []}
    body = _serper_search(_search_query(query))
    if body is None:
        return {"retrieval_status": "unavailable", "related_sources": []}
    query_terms = _informative_terms(query)
    if not query_terms:
        return {"retrieval_status": "no_results", "related_sources": []}
    candidates = _relevant_sources(body, query_terms, query, excluded_domain)
    if not candidates:
        focused_body = _serper_search(_focused_search_query(query))
        if focused_body is not None:
            candidates = _relevant_sources(focused_body, query_terms, query, excluded_domain)
    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    sources = [source for _score, source in candidates[:config.SERPER_MAX_RESULTS]]
    return {
        "retrieval_status": "available" if sources else "no_results",
        "related_sources": sources,
    }
