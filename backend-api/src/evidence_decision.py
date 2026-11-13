"""Conservative claim-level evidence gate for the existing two public labels."""
from __future__ import annotations

import re
from urllib.parse import urlparse

try:
    from .retrieval import TRUSTED_DOMAIN_SUFFIXES, _informative_terms, _explicit_event_dates, _explicit_event_years, _peso_amounts, _person_entity_anchors, _canonical_term, _without_post_metadata_dates
except ImportError:
    from retrieval import TRUSTED_DOMAIN_SUFFIXES, _informative_terms, _explicit_event_dates, _explicit_event_years, _peso_amounts, _person_entity_anchors, _canonical_term, _without_post_metadata_dates


_ASSERTION_VERBS = {
    "prevents": "prevent", "prevented": "prevent", "preventing": "prevent",
    "causes": "cause", "caused": "cause", "causing": "cause",
    "reduces": "reduce", "reduced": "reduce", "reducing": "reduce",
    "increases": "increase", "increased": "increase", "increasing": "increase",
    "supports": "support", "supported": "support", "supporting": "support",
    "improves": "improve", "improved": "improve", "improving": "improve",
    "treats": "treat", "treated": "treat", "treating": "treat",
    "rollbacks": "rollback",
}
_MATERIAL_ACTIONS = {
    "seize", "destroy", "arrest", "kill", "shoot", "open", "approve", "file",
    "charge", "prevent", "cause", "reduce", "increase", "support", "improve",
    "treat", "cure", "recommend", "privatize", "return", "suspend", "resign",
    "relationship", "spy", "rollback",
}


def _evidence_terms(text: str) -> set[str]:
    text = re.sub(r"\b(?:has\s+)?called\s+it\s+quits\b", "resigned", text, flags=re.I)
    text = re.sub(r"\broll(?:s|ed|ing)?\s+back\b", "rollback", text, flags=re.I)
    text = re.sub(r"\bpump\s+prices?\b", "fuel price", text, flags=re.I)
    text = re.sub(r"\b(?:coming|next|upcoming)\s+week\b", "future week", text, flags=re.I)
    text = re.sub(r"\b(?:motorists?|drivers?)\b|\bshould\s+expect\b|\bexpect(?:s|ed)?\b", " ", text, flags=re.I)
    text = re.sub(r"\banother\s+round\s+of\b", " ", text, flags=re.I)
    return {_ASSERTION_VERBS.get(term, term) for term in _informative_terms(text)}


def _is_trusted_source(url: str | None) -> bool:
    host = (urlparse(url or "").hostname or "").casefold().removeprefix("www.")
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in TRUSTED_DOMAIN_SUFFIXES)


def _publisher_key(url: str | None) -> str:
    host = (urlparse(url or "").hostname or "").casefold().removeprefix("www.")
    matching_publishers = [
        suffix for suffix in TRUSTED_DOMAIN_SUFFIXES
        if host == suffix or host.endswith(f".{suffix}")
    ]
    return max(matching_publishers, key=len, default=host)


def _words(value: str) -> list[str]:
    return re.findall(r"[^\W_]+", value.casefold(), flags=re.UNICODE)


def _body_shingles(value: str, size: int = 5) -> set[tuple[str, ...]]:
    words = _words(value)
    if len(words) < size:
        return {tuple(words)} if words else set()
    return {tuple(words[index:index + size]) for index in range(len(words) - size + 1)}


def _independent_trusted_sources(
    assessments: list[dict],
    related_sources: list[dict],
) -> list[dict]:
    sources_by_url = {source.get("url"): source for source in related_sources}
    independent = []
    seen_publishers = set()
    seen_bodies = []
    for assessment in assessments:
        url = assessment.get("url")
        source = sources_by_url.get(url)
        if not source or not _is_trusted_source(url):
            continue
        publisher = _publisher_key(url)
        if publisher in seen_publishers:
            continue
        shingles = _body_shingles(source.get("article_text", ""))
        if not shingles or any(
            len(shingles & previous) / len(shingles | previous) >= 0.9
            for previous in seen_bodies
        ):
            continue
        seen_publishers.add(publisher)
        seen_bodies.append(shingles)
        independent.append(assessment)
    return independent


def _claim_qualifiers(value: str) -> set[str]:
    qualifiers = set(_words(value)) & {
        "umano", "alleged", "allegedly", "suspected", "reportedly",
        "hindi", "not", "no", "never",
    }
    if "allegedly" in qualifiers:
        qualifiers.discard("allegedly")
        qualifiers.add("alleged")
    if "reportedly" in qualifiers:
        qualifiers.discard("reportedly")
        qualifiers.add("reported")
    return qualifiers


def _negates_material_action(words: list[str], actions: set[str]) -> bool:
    negations = {"umano", "hindi", "not", "no", "never"}
    expectation_verbs = {"expect", "expects", "expected", "expecting", "predict", "predicts", "predicted", "forecast", "forecasts", "forecasted"}
    for position, word in enumerate(words):
        if word not in negations:
            continue
        following = words[position + 1:position + 11]
        if (any(_canonical_term(candidate) in actions for candidate in following)
                or any(candidate in expectation_verbs for candidate in following)):
            return True
    return False


def _sentences(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", value) if part.strip()]


def _material_numbers(value: str) -> set[str]:
    return {number.replace(",", "") for number in re.findall(r"(?<!\d)\d[\d,]*(?:\.\d+)?(?!\d)", value)}


def _material_locations(value: str) -> set[str]:
    # Only explicit place phrases are used. We do not guess locations from
    # unrelated capitalized words in a headline or publisher name.
    return {match.casefold() for match in re.findall(
        r"\b(?:in|sa|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", value)}


def _material_support(claim: str, body: str) -> tuple[str, str]:
    """Find a bounded direct article assertion with matching material anchors.

    This is a conservative paraphrase check, not general semantic entailment.
    It never turns a headline, search snippet, quote or publisher alone into
    support. Every count, amount, date, named person and explicit place in the
    claim must survive the comparison.
    """
    claim_text = _without_post_metadata_dates(claim)
    claim_terms = _evidence_terms(claim_text)
    actions = claim_terms & _MATERIAL_ACTIONS
    claim_numbers = _material_numbers(claim_text)
    if len(claim_terms) < (2 if claim_numbers else 3) or not actions:
        return "related", "No direct material assertion could be established from the article body."
    claim_amounts = _peso_amounts(claim_text)
    claim_dates = _explicit_event_dates(claim_text)
    claim_years = _explicit_event_years(claim_text)
    claim_people = _person_entity_anchors(claim_text)
    claim_places = _material_locations(claim_text)
    claim_qualifiers = _claim_qualifiers(claim_text)
    sentences = _sentences(body)
    for index in range(len(sentences)):
        for count in (1, 2, 3):
            window_parts = sentences[index:index + count]
            if len(window_parts) != count:
                continue
            window = " ".join(window_parts)
            lowered = window.casefold()
            if (any(part.lstrip().startswith(('"', '“', "'", '‘', '>')) for part in window_parts)
                    or '?' in window or re.search(r"\b(?:viral post|social media post|post claims?|rumou?rs?|hypothetical|debunked|false|fake|misleading|untrue|incorrect)\b", lowered)):
                continue
            terms = _evidence_terms(window)
            minimum_overlap = 2 if claim_numbers else 3
            if not actions <= terms or len(claim_terms & terms) < max(minimum_overlap, (len(claim_terms) * 3 + 3) // 4):
                continue
            if not claim_numbers <= _material_numbers(window):
                continue
            if claim_years and not claim_years <= _explicit_event_years(window):
                continue
            if claim_amounts and not claim_amounts <= _peso_amounts(window):
                continue
            if claim_dates and not claim_dates <= _explicit_event_dates(window):
                continue
            if claim_people and not claim_people <= _person_entity_anchors(window):
                continue
            if claim_places and not claim_places <= _material_locations(window):
                continue
            action_context = " ".join(
                part for part in window_parts if actions & _evidence_terms(part)
            )
            action_words = _words(action_context)
            window_qualifiers = _claim_qualifiers(action_context)
            if not claim_qualifiers <= window_qualifiers:
                continue
            if not claim_qualifiers and window_qualifiers & {"umano", "alleged", "allegedly", "reportedly"}:
                continue
            if not claim_qualifiers and _negates_material_action(action_words, actions):
                continue
            return "supports", window[:500]
    return "related", "The readable article did not establish every material action, person, place, date, number and qualification in the claim."


def _article_relation(claim: str, body: str) -> tuple[str, str]:
    """Require a direct prose assertion, including all numbers and qualifiers."""
    claim_words = _words(claim)
    if len(claim_words) < 5 or len(claim_words) > 90:
        return "related", "The claim cannot be checked by the strict assertion gate."
    phrase = " ".join(claim_words)
    for sentence in _sentences(body):
        sentence_words = _words(sentence)
        joined = " ".join(sentence_words)
        # Match complete tokens; Monday must not match Mondayish, for example.
        match = re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", joined)
        if match is None:
            continue
        prefix = joined[:match.start()].strip()
        # A quoted/report-attributed statement is not the publisher's verdict.
        # Check this BEFORE interpreting words such as "false" in the prefix.
        if sentence.startswith(('"', '“', "'", '‘', '>')) or any(
            re.search(r"\b" + cue + r"\b", prefix)
            for cue in ("claims?", "claimed", "says?", "said", "rumou?rs?", "viral posts?", "alleged", "unverified", "quoted?", "ayon", "umano", "post", "posts")
        ):
            continue
        hypothetical = {"if", "whether", "would", "could", "might", "should", "kung", "sakali", "sana"}
        if ('?' in sentence or set(sentence_words) & hypothetical
                or any(mark in sentence for mark in ('"', '“', '”'))):
            continue
        # Only a standalone explicit verdict marker may establish a debunk.
        # "not false", "not misleading" and discussions of misinformation do not.
        debunk = re.match(r"^(?:false|fake|misleading|untrue|incorrect|debunked|mali|peke|huwad)\s*:\s*", sentence, re.I)
        if debunk and prefix in {"false", "fake", "misleading", "untrue", "incorrect", "debunked", "mali", "peke", "huwad"}:
            return "contradicts", sentence[:500]
        # Mentioning an exact claim inside a question, hypothetical or embedded
        # quotation does not assert that it happened. Keep these as reading only.
        if prefix:
            continue
        material_qualifiers = {"umano", "alleged", "allegedly", "suspected", "reportedly", "hindi", "not", "no", "never"}
        if (set(sentence_words) & material_qualifiers) != (set(claim_words) & material_qualifiers):
            continue
        if any(re.search(r"\b" + cue + r"\b", joined) for cue in ("false", "fake", "misleading", "untrue", "incorrect", "debunked", "mali", "peke", "huwad")):
            continue
        return "supports", sentence[:500]
    return _material_support(claim, body)


def _headline_has_body_corroboration(claim: str, title: str, body: str) -> bool:
    headline_relation, _ = _article_relation(claim, title)
    if headline_relation != "supports":
        return False
    claim_text = _without_post_metadata_dates(claim)
    claim_terms = _evidence_terms(claim_text)
    body_terms = _evidence_terms(body)
    if not claim_terms or not claim_terms <= body_terms:
        return False
    actions = claim_terms & _MATERIAL_ACTIONS
    subject_terms = claim_terms - actions
    sentences = _sentences(body)
    corroborated_in_body = False
    claim_qualifiers = _claim_qualifiers(claim_text)
    for index in range(len(sentences)):
        for width in (1, 2, 3):
            if index + width > len(sentences):
                continue
            window = " ".join(sentences[index:index + width])
            window_terms = _evidence_terms(window)
            action_context = " ".join(
                sentence for sentence in sentences[index:index + width]
                if actions & _evidence_terms(sentence)
            )
            action_words = _words(action_context)
            window_qualifiers = _claim_qualifiers(action_context)
            if claim_qualifiers and not claim_qualifiers <= window_qualifiers:
                continue
            if not claim_qualifiers and window_qualifiers & {
                "umano", "alleged", "allegedly", "suspected", "reportedly",
            }:
                continue
            if not claim_qualifiers and _negates_material_action(action_words, actions):
                continue
            if (actions <= window_terms
                    and len(subject_terms & window_terms) >= min(2, len(subject_terms))):
                corroborated_in_body = True
                break
        if corroborated_in_body:
            break
    if not corroborated_in_body:
        return False
    return (
        _material_numbers(claim_text) <= _material_numbers(body)
        and _explicit_event_dates(claim_text) <= _explicit_event_dates(body)
        and _explicit_event_years(claim_text) <= _explicit_event_years(body)
        and _person_entity_anchors(claim_text) <= _person_entity_anchors(body)
    )


def apply_evidence(model_prediction: dict, related_sources: list[dict], fact_check_matches: list[dict], claim: str = "") -> dict:
    assessments = []
    for source in related_sources:
        body = source.get("article_text", "") if source.get("content_status") == "readable" else ""
        relationship, reason = _article_relation(claim, body) if body and claim else ("unverified", "The full article could not be assessed.")
        if (relationship == "related" and body and claim
                and _headline_has_body_corroboration(claim, source.get("title", ""), body)):
            relationship = "supports"
            reason = "The publisher headline states the complete claim, and the readable article body corroborates its material details."
        assessments.append({"url": source.get("url"), "relationship": relationship, "reason": reason})
    supports = [item for item in assessments if item["relationship"] == "supports"]
    contradicts = [item for item in assessments if item["relationship"] == "contradicts"]
    independent_supports = _independent_trusted_sources(supports, related_sources)
    independent_contradictions = _independent_trusted_sources(contradicts, related_sources)
    credible_supports = [
        item for item in supports if _is_trusted_source(item.get("url"))
    ]
    credible_contradictions = [
        item for item in contradicts if _is_trusted_source(item.get("url"))
    ]
    sufficient_support = len(independent_supports) >= 2 and not credible_contradictions
    sufficient_contradiction = len(independent_contradictions) >= 2 and not credible_supports
    if sufficient_support:
        label, internal, relationship = "No Misleading Information Detected", "Non-Misleading", "supports"
        basis = "Two independent readable trusted publishers directly support the complete claim and its material details, with no readable trusted source directly contradicting it."
        chosen = independent_supports
    elif sufficient_contradiction:
        label, internal, relationship = "Potentially Misleading", "Misleading", "contradicts"
        basis = "Two independent readable trusted publishers directly contradict the complete claim, with no readable trusted source supporting it."
        chosen = independent_contradictions
    else:
        label, internal = model_prediction["public_label"], model_prediction["internal_label"]
        relationship = (
            "conflicting" if credible_supports and credible_contradictions
            else "supports" if credible_supports
            else "contradicts" if credible_contradictions
            else "related" if any(item["relationship"] == "related" for item in assessments)
            else "unverified" if assessments or fact_check_matches
            else "not_assessed"
        )
        basis = "Available evidence does not meet the two-independent-publisher threshold or is conflicting; the final label follows the hybrid model."
        chosen = []
    return {
        "internal_label": internal, "public_label": label,
        "decision_source": "verified_evidence" if chosen else "screening_model",
        "decision_basis": basis, "evidence_relationship": relationship,
        "supporting_source_count": len(credible_supports), "strong_fact_check_matches": [],
        "evidence_assessments": assessments,
        "evidence_urls": [item["url"] for item in chosen],
        "evidence_adjusted": label != model_prediction["public_label"],
    }
