"""Independent server-side Serper.dev retrieval for related-source context."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from decimal import Decimal
from datetime import date
from urllib import error, request
from urllib.parse import urlparse

import config
try:
    from .provider_http import open_provider, read_json, safe_link
    from .article_reader import read_article
except ImportError:
    from provider_http import open_provider, read_json, safe_link
    from article_reader import read_article

logger = logging.getLogger(__name__)

def _source_name(item: dict) -> str:
    link = str(item.get("link", ""))
    return str(item.get("source") or urlparse(link).netloc or "").removeprefix("www.")


SOCIAL_DOMAINS = {
    "facebook.com", "fb.com", "instagram.com", "tiktok.com", "x.com", "twitter.com",
    "youtube.com", "youtu.be", "reddit.com", "redd.it", "threads.net", "telegram.org",
}
TRUSTED_DOMAIN_SUFFIXES = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "npr.org", "cnn.com",
    "nytimes.com", "washingtonpost.com", "theguardian.com", "cbsnews.com", "nbcnews.com",
    "abcnews.go.com", "pbs.org", "aljazeera.com", "dw.com", "france24.com", "euronews.com",
    "cbc.ca", "abc.net.au", "channelnewsasia.com", "straitstimes.com", "scmp.com",
    "thehindu.com", "indianexpress.com", "bangkokpost.com", "jakartapost.com", "vnexpress.net",
    "who.int", "un.org", "cdc.gov", "nhs.uk", "snopes.com", "politifact.com",
    "factcheck.org", "fullfact.org", "leadstories.com", "afp.com", "factcheck.afp.com",
    "inquirer.net", "rappler.com",
    "gmanetwork.com", "abs-cbn.com", "philstar.com", "pna.gov.ph", "officialgazette.gov.ph",
    "gov.ph", "doh.gov.ph", "comelec.gov.ph", "edu.ph", "verafiles.org",
    "mb.com.ph", "manilastandard.net", "manilatimes.net", "businessmirror.com.ph",
    "bworldonline.com", "sunstar.com.ph", "cnnphilippines.com", "pia.gov.ph", "tribune.net.ph",
    "andasian.com",
}
PHILIPPINE_PUBLISHER_SUFFIXES = {
    "inquirer.net", "rappler.com", "verafiles.org", "gmanetwork.com",
    "abs-cbn.com", "philstar.com", "pna.gov.ph", "officialgazette.gov.ph",
    "gov.ph", "doh.gov.ph", "comelec.gov.ph", "edu.ph", "mb.com.ph",
    "manilastandard.net", "manilatimes.net", "businessmirror.com.ph",
    "bworldonline.com", "sunstar.com.ph", "cnnphilippines.com", "pia.gov.ph",
    "tribune.net.ph",
}
FOCUSED_NEWS_DOMAINS = (
    "gmanetwork.com", "abs-cbn.com", "inquirer.net", "rappler.com", "philstar.com",
    "mb.com.ph", "manilastandard.net", "manilatimes.net", "businessmirror.com.ph",
    "bworldonline.com", "sunstar.com.ph", "cnnphilippines.com", "pna.gov.ph", "pia.gov.ph",
    "verafiles.org", "tribune.net.ph", "reuters.com", "apnews.com", "bbc.com",
    "bbc.co.uk", "npr.org", "cnn.com", "theguardian.com", "aljazeera.com",
    "channelnewsasia.com", "straitstimes.com", "who.int", "cdc.gov", "nhs.uk",
)

# Terms that are frequent in prose, social-post chrome, or dates do not establish
# that a search result discusses the same event.  Keep this deliberately small and
# language-neutral enough for English/Filipino/Taglish news text.
RELEVANCE_STOP_WORDS = {
    "and", "are", "for", "can", "help", "helps", "enough", "worth", "consisting",
    "news", "photo", "pholo",
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
    # Match routine headline present tense to reported past tense during
    # discovery and article assessment. This does not itself prove a claim.
    "opens": "open", "opened": "open", "opening": "open",
    "approves": "approve", "approved": "approve", "approving": "approve",
    "files": "file", "filed": "file", "filing": "file",
    "charges": "charge", "charged": "charge", "charging": "charge",
    "recommends": "recommend", "recommended": "recommend", "recommending": "recommend",
    "creates": "create", "created": "create", "creating": "create", "creation": "create",
    "adopts": "adopt", "adopted": "adopt", "adopting": "adopt", "adoption": "adopt",
    "offers": "offer", "offered": "offer", "offering": "offer",
    "prevents": "prevent", "prevented": "prevent", "preventing": "prevent",
    "causes": "cause", "caused": "cause", "causing": "cause",
    "reduces": "reduce", "reduced": "reduce", "reducing": "reduce",
    "increases": "increase", "increased": "increase", "increasing": "increase",
    "supports": "support", "supported": "support", "supporting": "support",
    "improves": "improve", "improved": "improve", "improving": "improve",
    "treats": "treat", "treated": "treat", "treating": "treat",
    "boc": "customs", "lto": "transportation", "smuggled": "illicit",
    "suspend": "suspend", "suspends": "suspend", "suspended": "suspend",
    "suspending": "suspend", "suspension": "suspend", "suspensions": "suspend",
    "mrt": "metro", "isapribado": "privatize", "maisapribado": "privatize",
    "planong": "target",
    "privatization": "privatize", "privatized": "privatize", "privatised": "privatize",
    "privatise": "privatize", "privatising": "privatize", "privatizing": "privatize",
    "returning": "return", "returned": "return", "returns": "return", "comeback": "return",
    "quit": "resign", "quits": "resign", "resigned": "resign", "resigns": "resign",
    "resignation": "resign", "resignations": "resign", "stepped": "resign", "steps": "resign",
    "revelation": "report", "revelations": "report", "reported": "report", "reports": "report",
    "affair": "relationship", "affairs": "relationship", "extramarital": "relationship",
    "relationship": "relationship", "relationships": "relationship",
    "seized": "seize", "seizure": "seize", "seizes": "seize",
    "confiscated": "seize", "intercepted": "seize",
    "destroyed": "destroy", "destroys": "destroy", "destroying": "destroy",
    "crushed": "destroy", "condemned": "destroy",
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
    normalized = re.sub(r"\b(?:department\s+of\s+justice|justice\s+department|doj)\b", "doj", normalized)
    normalized = re.sub(r"\b(?:photo|pholo)\s+pia\b", " ", normalized)
    normalized = re.sub(r"\bnews\s*$", " ", normalized)
    terms = set(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))
    return {
        _canonical_term(term) for term in terms
        if len(term) >= 3 and not term.isdigit() and term not in RELEVANCE_STOP_WORDS
    }


def _ordered_informative_terms(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", _without_post_metadata_dates(text)).casefold()
    normalized = re.sub(r"\b(?:photo|pholo)\s+pia\b", " ", normalized)
    normalized = re.sub(r"\bnews\s*$", " ", normalized)
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
        if len(name_words) >= 2 and (had_title or (has_connector and len(normalized) >= 3)):
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


def _location_anchors(text: str) -> set[str]:
    location_pattern = r"([A-Z][a-z]+(?:[\s-]+[A-Z][a-z]+){0,2})"
    locations = {
        location for location in re.findall(
            r"\b(?:in|at|from|near|to|sa)\s+" + location_pattern + r"\b",
            text,
        )
        if location.casefold() not in {"host", "hold", "stage"}
    }
    for location in re.findall(
        r"\b" + location_pattern + r"\s+(?:[Tt]o|[Ww]ill|[Ww]ould)\s+(?:[Hh]ost|[Hh]old|[Ss]tage)\b",
        text,
    ):
        words = location.split()
        while words and words[0].casefold() in {"announced", "reported", "revealed", "said"}:
            words.pop(0)
        if words:
            locations.add(" ".join(words))
    return {" ".join(location.casefold().split()) for location in locations}


def _peso_amounts(text: str) -> set[Decimal]:
    """Compare Philippine currency amounts across headline abbreviations."""
    number = r"(\d[\d,]*(?:\.\d+)?)"
    scale = r"(?:[\s-]*(billion|million|thousand|bn|mn|b|m|k)\b)?"
    patterns = (
        r"(?:₱|\bphp\s*|\bp\s*)" + number + scale,
        r"\b" + number + scale + r"\s*(?:philippine\s+)?pesos?\b",
    )
    multipliers = {"billion": 10**9, "bn": 10**9, "b": 10**9,
                   "million": 10**6, "mn": 10**6, "m": 10**6,
                   "thousand": 1000, "k": 1000, "": 1}
    amounts = set()
    for pattern in patterns:
        for amount, unit in re.findall(pattern, text.casefold()):
            amounts.add(Decimal(amount.replace(",", "")) * multipliers[unit])
    return amounts


def _entity_and_content_alignment(query: str, item: dict) -> bool:
    candidate = " ".join((str(item.get("title", "")), str(item.get("snippet", "")), str(item.get("link", ""))))
    claim_text = _without_post_metadata_dates(query)
    claim_amounts = _peso_amounts(query)
    candidate_amounts = _peso_amounts(candidate)
    if claim_amounts and candidate_amounts and claim_amounts.isdisjoint(candidate_amounts):
        return False
    claim_dates = _explicit_event_dates(claim_text)
    candidate_dates = _explicit_event_dates(candidate)
    if claim_dates and candidate_dates and claim_dates.isdisjoint(candidate_dates):
        return False
    claim_years = _explicit_event_years(claim_text)
    if claim_years and not claim_years <= _explicit_event_years(candidate):
        return False
    if _contains_episodic_markers(candidate) and not _contains_episodic_markers(query):
        return False
    query_locations = _location_anchors(query)
    candidate_locations = set().union(*(
        _location_anchors(str(item.get(field, ""))) for field in ("title", "snippet", "link")
    ))
    if query_locations and not query_locations <= candidate_locations:
        return False
    query_people = _person_entity_anchors(query)
    if not query_people:
        return True
    candidate_people = _person_entity_anchors(candidate)
    return bool(query_people & candidate_people)


def _explicit_event_dates(text: str) -> set[date]:
    """Compare full dates actually written in the claim, never infer its year.

    Provider publication metadata is deliberately excluded: publication time
    and an event's date are different. Missing dates do not establish a match.
    """
    months = {name: index for index, names in enumerate((
        ('january', 'jan', 'enero'), ('february', 'feb', 'pebrero'),
        ('march', 'mar', 'marso'), ('april', 'apr', 'abril'), ('may', 'mayo'),
        ('june', 'jun', 'hunyo'), ('july', 'jul', 'hulyo'), ('august', 'aug', 'agosto'),
        ('september', 'sep', 'sept', 'setyembre'), ('october', 'oct', 'oktubre'),
        ('november', 'nov', 'nobyembre'), ('december', 'dec', 'disyembre'),
    ), 1) for name in names}
    name = '(' + '|'.join(months) + ')'
    result = set()
    def add(year, month, day):
        try: result.add(date(int(year), int(month), int(day)))
        except ValueError: pass
    lowered = text.casefold()
    for year, month, day in re.findall(r'\b(20\d{2}|19\d{2})-(\d{2})-(\d{2})\b', lowered):
        add(year, month, day)
    for month, day, year in re.findall(r'\b' + name + r'\.?\s+(\d{1,2}),?\s+(20\d{2}|19\d{2})\b', lowered):
        add(year, months[month], day)
    for day, month, year in re.findall(r'\b(\d{1,2})\s+(?:ng\s+)?' + name + r'\.?[,]?\s+(20\d{2}|19\d{2})\b', lowered):
        add(year, months[month], day)
    return result


def _explicit_event_years(text: str) -> set[str]:
    return set(re.findall(r"\b(?:19|20)\d{2}\b", text))


def _without_post_metadata_dates(text: str) -> str:
    months = (
        "january|jan|february|feb|march|mar|april|apr|may|june|jun|july|jul|"
        "august|aug|september|sep|sept|october|oct|november|nov|december|dec"
    )
    pattern = rf"\b(?:{months})\.?\s+\d{{1,2}},?\s+(?:19|20)\d{{2}}\b(?=\s*(?:news|photo|pholo|pia)\b)"
    return re.sub(pattern, " ", text, flags=re.IGNORECASE)


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


def _is_relevant(
    item: dict,
    query_terms: set[str],
    query: str = "",
    *,
    check_alignment: bool = True,
) -> tuple[bool, int]:
    matched_terms, title_matches, score = _relevance(item, query_terms)
    required_matches = len(query_terms) if len(query_terms) <= 5 else 3
    title_required = 2 if len(query_terms) > 5 else 1 if len(query_terms) >= 3 else 0
    aligned = _entity_and_content_alignment(query, item) if query and check_alignment else True
    return matched_terms >= required_matches and title_matches >= title_required and aligned, score


def _search_query(query: str, *, limit: int = 500) -> str:
    """Keep the claim searchable; social results are filtered after retrieval."""
    search_text = re.sub(
        r"https?://\S+|www\.\S+", " ",
        _without_post_metadata_dates(query),
        flags=re.IGNORECASE,
    )
    search_text = re.sub(r"\b(?:photo|pholo)\s+pia\b", " ", search_text, flags=re.IGNORECASE)
    search_text = re.sub(r"\bnews\s*$", " ", search_text, flags=re.IGNORECASE)
    search_text = re.sub(r"\bplanong\b", "target", search_text, flags=re.IGNORECASE)
    search_text = re.sub(r"\bisapribado\b", "maisapribado", search_text, flags=re.IGNORECASE)
    search_text = re.sub(r"\s+", " ", search_text).strip(" .-|\"")
    return search_text[:limit]


def _focused_search_query(query: str) -> str:
    """Search one material sentence with surface words and intact quantities.

    Canonical terms are useful for relevance checks, but search providers may
    not treat `illicit` as the same wording as a post's `smuggled`. Preserve
    the post's words here; the article-body gate still decides evidential use.
    """
    # Scan beyond the raw provider query's 500-character limit so a material
    # sentence after a social introduction can still be selected.
    cleaned = _search_query(query, limit=4000)
    protected = re.sub(
        r"\b(?:Mr|Mrs|Ms|Dr|Jr|Sr|Atty|Sen|Rep|Gov|Pres|Gen|Sec|Engr)\.",
        lambda match: match.group()[:-1] + "\ue000", cleaned, flags=re.I,
    )
    segments = [part.strip().replace("\ue000", ".") for part in
                re.split(r"(?<=[.!?])\s+|\n+", protected) if part.strip()]
    if not segments:
        return ""
    actions = {
        "destroy", "seize", "arrest", "open", "approve", "file", "charge",
        "create", "adopt", "offer", "prevent", "cause", "reduce", "increase",
        "support", "improve", "treat", "recommend", "return", "suspend",
        "resign", "call", "calls", "calling",
    }
    def priority(part: str) -> tuple[int, int, int]:
        terms = _informative_terms(part)
        has_amount_or_number = bool(re.search(r"\d", part))
        return (int(bool(terms & actions)), int(has_amount_or_number), min(len(terms), 20))
    segment = max(segments, key=priority)
    token_pattern = (
        r"(?<!\w)(?:₱|php\s*|p\s*)\d[\d,]*(?:\.\d+)?"
        r"(?:\s*(?:billion|million|thousand|bn|mn|b|m|k)\b)?"
        r"|\d[\d,]*(?:\.\d+)?|[^\W_]+"
    )
    noise = {"breaking", "watch", "follow", "page", "subscribe", "click", "friends", "details"}
    kept, seen = [], set()
    for token in re.findall(token_pattern, segment, flags=re.I | re.UNICODE):
        folded = token.casefold()
        if (folded in noise or
                (folded in RELEVANCE_STOP_WORDS and folded not in {"hindi", "umano", "not", "no"})):
            continue
        canonical = _canonical_term(folded)
        if canonical in seen:
            continue
        seen.add(canonical)
        kept.append(token)
        if len(kept) >= 14:
            break
    return " ".join(kept)


def _prefer_focused_first(query: str) -> bool:
    """Long/social prose benefits from a compact primary query; short news
    claims retain the original wording, which often retrieves better results.
    """
    cleaned = _search_query(query)
    return len(cleaned) > 180 or len(re.findall(r"[^\W_]+", cleaned)) > 28


def _is_blocked_domain(host: str, excluded_domain: str | None) -> bool:
    host = host.casefold().removeprefix("www.")
    excluded = (excluded_domain or "").casefold().removeprefix("www.")
    return any(host == domain or host.endswith(f".{domain}") for domain in SOCIAL_DOMAINS) or bool(excluded and (host == excluded or host.endswith(f".{excluded}")))


def _is_trusted_domain(host: str) -> bool:
    host = host.casefold().removeprefix("www.")
    return any(host == domain or host.endswith(f".{domain}") for domain in TRUSTED_DOMAIN_SUFFIXES)


def _is_philippine_publisher(host: str) -> bool:
    host = host.casefold().removeprefix("www.")
    return any(host == domain or host.endswith(f".{domain}") for domain in PHILIPPINE_PUBLISHER_SUFFIXES)


def _serper_search(search_query: str) -> dict | None:
    payload = json.dumps({"q": search_query, "num": 20, "gl": "ph", "hl": "en"}).encode("utf-8")
    req = request.Request(
        "https://google.serper.dev/search",
        data=payload,
        method="POST",
        headers={"X-API-KEY": config.SERPER_API_KEY, "Content-Type": "application/json"},
    )
    for attempt in range(2):
        try:
            with open_provider(req, timeout=config.SERPER_TIMEOUT_SECONDS) as response:
                return read_json(response)
        except error.HTTPError as exc:
            logger.warning("Serper search request rejected with HTTP %s.", exc.code)
            return None
        except error.URLError as exc:
            if attempt == 0 and isinstance(exc.reason, TimeoutError):
                logger.warning("Serper search timed out; retrying once.")
                continue
            logger.warning("Serper search connection failed (%s).", type(exc.reason).__name__)
            return None
        except TimeoutError:
            if attempt == 0:
                logger.warning("Serper search timed out; retrying once.")
                continue
            logger.warning("Serper search request timed out.")
            return None
        except ValueError as exc:
            logger.warning("Serper returned an invalid response (%s).", type(exc).__name__)
            return None
    return None


def _relevant_sources(body: dict, query_terms: set[str], query: str, excluded_domain: str | None, excluded_urls=()) -> list[tuple[int, dict]]:
    candidates = []
    for item in body.get("organic", []):
        url = str(item.get("link", "")).strip()
        title = str(item.get("title", "")).strip()
        host = urlparse(url).netloc
        relevant, relevance_score = _is_relevant(item, query_terms, query)
        if url not in excluded_urls and safe_link(url) and title and relevant and _is_trusted_domain(host) and not _is_blocked_domain(host, excluded_domain):
            candidates.append((relevance_score, {
                "title": title,
                "url": url,
                "snippet": str(item.get("snippet", "")).strip(),
                "source": _source_name(item),
                "date": item.get("date") or None,
                "kind": "search_result",
            }))
    # Choose the strongest candidate per publisher AFTER scoring every result.
    # Provider ordering must not let a weak headline hide a better same-site match.
    best_by_host = {}
    for score, source in candidates:
        host = urlparse(source['url']).hostname.casefold().removeprefix('www.')
        if host not in best_by_host or score > best_by_host[host][0]:
            best_by_host[host] = (score, source)
    return list(best_by_host.values())


def retrieve_related_sources(query: str, excluded_domain: str | None = None, *, focused: bool = False, excluded_urls=()) -> dict:
    if not config.SERPER_ENABLED:
        return {"retrieval_status": "disabled", "related_sources": []}
    if not config.SERPER_API_KEY:
        return {"retrieval_status": "unavailable_not_configured", "related_sources": []}
    query_terms = _informative_terms(query)
    if not query_terms:
        return {"retrieval_status": "no_results", "related_sources": []}
    focused_first = focused or _prefer_focused_first(query)
    focused_query = _focused_search_query(query)
    raw_query = _search_query(query)
    if focused_first and not focused_query:
        focused_first = False
    primary_query = focused_query if focused_first else raw_query
    if not primary_query:
        return {"retrieval_status": "no_results", "related_sources": []}
    body = _serper_search(primary_query)
    if body is None:
        return {"retrieval_status": "unavailable", "related_sources": []}
    candidates = _relevant_sources(body, query_terms, query, excluded_domain, excluded_urls)
    focused_used = focused_first
    if len(candidates) < 2 and not focused:
        alternate_query = raw_query if focused_first else focused_query
        if alternate_query and alternate_query.casefold() != primary_query.casefold():
            alternate_body = _serper_search(alternate_query)
            focused_used = True
            if alternate_body is not None:
                alternate = _relevant_sources(alternate_body, query_terms, query, excluded_domain, excluded_urls)
                seen_urls = {source['url'] for _score, source in candidates}
                seen_hosts = {urlparse(source['url']).hostname for _score, source in candidates}
                candidates.extend((score, source) for score, source in alternate
                                  if source['url'] not in seen_urls
                                  and urlparse(source['url']).hostname not in seen_hosts)
    # Prefer local reporting at equal relevance, but do not discard a direct
    # international health/source article just because one Philippine hit exists.
    # The readable body and claim gate still decide whether either is evidence.
    candidates.sort(key=lambda candidate: (
        candidate[0],
        _is_philippine_publisher(urlparse(candidate[1]["url"]).hostname or ""),
    ), reverse=True)
    sources = [source for _score, source in candidates[:config.SERPER_MAX_RESULTS]]
    return {
        "retrieval_status": "available" if sources else "no_results",
        "related_sources": sources,
        "focused_used": focused_used,
    }


def inspect_related_sources(sources: list[dict], claim: str) -> list[dict]:
    """Replace search metadata with title/excerpt from each fetched article.

    Inaccessible pages remain traceable as URLs but have no displayed search
    title or snippet and cannot influence the evidence decision.
    """
    inspected = []
    query_terms = _informative_terms(claim)
    for item in sources:
        url = item.get("url", "")
        article = read_article(url, allowed_host=_is_trusted_domain)
        if article.get("content_status") != "readable":
            inspected.append({
                "url": url,
                "source": _source_name({"link": url}),
                "content_status": "inaccessible",
                "relationship": "unverified",
                "search_title": item.get("title"),
                "search_snippet": item.get("snippet"),
                "date": item.get("date"),
                **({"origin": item["origin"]} if item.get("origin") else {}),
            })
            continue
        paragraphs = article["article_text"].split("\n")
        excerpt = max(paragraphs, key=lambda part: len(_informative_terms(part) & query_terms), default="")
        # Search metadata can be stale; full liveblog bodies can also contain
        # unrelated updates that trip event-specific alignment guards.
        relevant, _score = _is_relevant(
            {"title": article["title"], "snippet": article["article_text"], "link": url},
            query_terms, claim, check_alignment=False,
        )
        if not relevant and item.get("origin") != "post_link":
            continue
        inspected.append({"url": url, "title": article["title"], "source": _source_name({"link": url}),
                          "snippet": excerpt[:500], "article_text": article["article_text"],
                          "content_status": "readable", "date": item.get("date"),
                          **({"origin": item["origin"]} if item.get("origin") else {})})
    return inspected
