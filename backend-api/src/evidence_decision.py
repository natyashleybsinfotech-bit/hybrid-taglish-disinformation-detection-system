"""Conservative claim-level evidence gate for the existing two public labels."""
from __future__ import annotations

import re
from urllib.parse import urlparse
import config
try:
    from . import local_nli
except ImportError:
    import local_nli


try:
    from .retrieval import TRUSTED_DOMAIN_SUFFIXES, _informative_terms, _explicit_event_dates, _explicit_event_years, _peso_amounts, _person_entity_anchors, _canonical_term, _without_post_metadata_dates
except ImportError:
    from retrieval import TRUSTED_DOMAIN_SUFFIXES, _informative_terms, _explicit_event_dates, _explicit_event_years, _peso_amounts, _person_entity_anchors, _canonical_term, _without_post_metadata_dates


_ASSERTION_VERBS = {
    "expecting": "expect",
    "advocates": "advocate", "advocated": "advocate", "advocating": "advocate",
    "prevents": "prevent", "prevented": "prevent", "preventing": "prevent",
    "causes": "cause", "caused": "cause", "causing": "cause",
    "reduces": "reduce", "reduced": "reduce", "reducing": "reduce",
    "increases": "increase", "increased": "increase", "increasing": "increase",
    "supports": "support", "supported": "support", "supporting": "support",
    "improves": "improve", "improved": "improve", "improving": "improve",
    "treats": "treat", "treated": "treat", "treating": "treat",
    "creates": "create", "created": "create", "creating": "create", "creation": "create",
    "adopts": "adopt", "adopted": "adopt", "adopting": "adopt", "adoption": "adopt",
    "offers": "offer", "offered": "offer", "offering": "offer",
    "rollbacks": "rollback",
}
_MATERIAL_ACTIONS = {
    "seize", "destroy", "arrest", "kill", "shoot", "open", "approve", "file",
    "charge", "prevent", "cause", "reduce", "increase", "support", "improve",
    "treat", "cure", "recommend", "privatize", "return", "suspend", "resign",
    "relationship", "spy", "rollback", "create", "adopt", "offer", "advocate", "expect",
}


def _evidence_terms(text: str) -> set[str]:
    # Only normalize the explicit future-child phrase; welcoming a child in
    # general could describe a birth that already happened.
    text = re.sub(r"\bprepar(?:es|ing)\s+to\s+welcome\s+(?=(?:their|a|the)\s+(?:first\s+)?(?:child|baby)\b)", "expecting ", text, flags=re.I)
    # A call for a change is evidence of advocacy, not proof that the change
    # happened. Keep this action distinct from approve/implement/pay.
    text = re.sub(r"\b(?:calls?|called|calling)\s+for\b", "advocates", text, flags=re.I)
    text = re.sub(r"\b(?:pay|salaries|salary)\b", "salary", text, flags=re.I)
    text = re.sub(r"\bteachers?\b", "teacher", text, flags=re.I)
    text = re.sub(r"\b(?:bigger|larger|higher)\b", "higher", text, flags=re.I)
    text = re.sub(r"\b(?:has\s+)?called\s+it\s+quits\b", "resigned", text, flags=re.I)
    text = re.sub(r"\broll(?:s|ed|ing)?\s+back\b", "rollback", text, flags=re.I)
    text = re.sub(r"\bpump\s+prices?\b", "fuel price", text, flags=re.I)
    text = re.sub(r"\b(?:coming|next|upcoming)\s+week\b", "future week", text, flags=re.I)
    text = re.sub(r"\b(?:motorists?|drivers?)\b|\bshould\s+expect\b|\bexpect(?:s|ed)?\b", " ", text, flags=re.I)
    text = re.sub(r"\banother\s+round\s+of\b", " ", text, flags=re.I)
    return {_ASSERTION_VERBS.get(term, term) for term in _informative_terms(text)}


def _is_trusted_source(url: str | None) -> bool:
    if urlparse(url or "").scheme not in {"http", "https"}:
        return False
    host = (urlparse(url or "").hostname or "").casefold().removeprefix("www.")
    return any(host == suffix or host.endswith(f".{suffix}") for suffix in TRUSTED_DOMAIN_SUFFIXES)


def _publisher_key(url: str | None) -> str:
    host = (urlparse(url or "").hostname or "").casefold().removeprefix("www.")
    matching_publishers = [
        suffix for suffix in TRUSTED_DOMAIN_SUFFIXES
        if host == suffix or host.endswith(f".{suffix}")
    ]
    return max(matching_publishers, key=len, default=host)


def _primary_authority_for_claim(url: str | None, claim: str) -> str | None:
    """Narrow authority scopes; a generic government hostname is not sufficient."""
    host = (urlparse(url or '').hostname or '').casefold().removeprefix('www.')
    terms = _evidence_terms(claim)
    health = {'water', 'dehydration', 'vaccine', 'vaccination', 'disease', 'health', 'infection', 'symptom', 'antibiotic', 'antibiotics', 'virus', 'viruses', 'bacteria', 'bacterial'}
    rules = {
        'cdc.gov': ('CDC public-health guidance', health),
        'who.int': ('WHO public-health guidance', health),
        'doh.gov.ph': ('DOH public-health guidance', health),
        'customs.gov.ph': ('Bureau of Customs report', {'customs'}),
    }
    for domain, (authority, subjects) in rules.items():
        if (host == domain or host.endswith('.' + domain)) and terms & subjects:
            return authority
    return None


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
        if (bool(actions & _evidence_terms(" ".join(following)))
                or any(candidate in expectation_verbs for candidate in following)):
            return True
    return False


def _sentences(value: str) -> list[str]:
    # Some readable publisher bodies concatenate paragraphs as "lives.In a ...".
    # Recover those boundaries so one long block does not hide a direct claim.
    # Protect common name/title abbreviations in both the post and article.
    # Otherwise "Marcos Jr. signed" becomes two separate claims.
    protected = re.sub(
        r"\b(?:Mr|Mrs|Ms|Dr|Jr|Sr|Atty|Sen|Rep|Gov|Pres|Gen|Sec|Engr)\.",
        lambda match: match.group()[:-1] + "\ue000", value, flags=re.I,
    )
    return [part.strip().replace("\ue000", ".") for part in re.split(
        r"(?<=[.!?])(?:\s+|(?=[A-Z]))|\n+", protected,
    ) if part.strip()]


def _material_numbers(value: str) -> set[str]:
    numbers = {number.replace(",", "") for number in re.findall(r"(?<!\d)\d[\d,]*(?:\.\d+)?(?!\d)", value)}
    spelled = {
        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'ten': '10', 'eleven': '11', 'twelve': '12', 'thirteen': '13',
        'fourteen': '14', 'fifteen': '15', 'sixteen': '16', 'seventeen': '17',
        'eighteen': '18', 'nineteen': '19', 'twenty': '20',
        'isa': '1', 'isang': '1', 'dalawa': '2', 'dalawang': '2',
        'tatlo': '3', 'tatlong': '3', 'apat': '4', 'limang': '5',
        'lima': '5', 'anim': '6', 'pito': '7', 'walo': '8', 'siyam': '9', 'sampu': '10',
    }
    numbers.update(spelled[word] for word in _words(value) if word in spelled)
    return numbers


def _material_locations(value: str) -> set[str]:
    # Only explicit place phrases are used. We do not guess locations from
    # unrelated capitalized words in a headline or publisher name.
    aliases = {'maynila': 'manila', 'lungsod ng maynila': 'manila',
               'lungsod ng quezon': 'quezon city', 'lungsod quezon': 'quezon city',
               'lungsod ng pasay': 'pasay city', 'lungsod ng cebu': 'cebu city'}
    phrases = re.findall(
        r"\b(?:in|sa|at)\s+((?:[Ll]ungsod\s+(?:ng\s+)?)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", value)
    return {aliases.get(match.casefold(), match.casefold()) for match in phrases}


def _named_actor_anchors(value: str) -> set[str]:
    """Preserve explicit multiword names even without a title such as Senator.

    These are conservative text anchors, not a claim to perform complete NER.
    An article about another person must not satisfy a semantic support check.
    """
    matches = re.findall(r"\b[A-Z][a-z]+(?:\s+(?:(?:de|del|dela|of|the)\s+)?[A-Z][a-z]+){1,4}\b", value)
    anchors = set()
    for match in matches:
        words = _words(match)
        while words and words[0] in {'the', 'ang', 'sa', 'si', 'ayon', 'look', 'president', 'senator', 'dr'}:
            words.pop(0)
        if len(words) >= 2:
            anchors.add(' '.join(words))
    return anchors


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
    # For creation/adoption/offer news, the named actor before the action is
    # material. A story about a different actor must not satisfy a headline.
    claim_words = _words(claim_text)
    first_action = next((index for index, word in enumerate(claim_words)
                         if _ASSERTION_VERBS.get(_canonical_term(word), _canonical_term(word)) in actions), None)
    actor_terms = (_evidence_terms(" ".join(claim_words[:first_action]))
                   if first_action is not None and actions & {"create", "adopt", "offer"} else set())
    sentences = _sentences(body)
    best_window = None
    for index in range(len(sentences)):
        for count in (1, 2, 3):
            window_parts = sentences[index:index + count]
            if len(window_parts) != count:
                continue
            window = " ".join(window_parts)
            if len(window) > 1600:
                continue
            lowered = window.casefold()
            if (any(part.lstrip().startswith(('"', '“', "'", '‘', '>')) for part in window_parts)
                    or '?' in window or re.search(r"\b(?:if|whether|would|could|might|kung|sakali|viral post|social media post|post claims?|rumou?rs?|hypothetical|debunked|false|fake|misleading|untrue|incorrect)\b", lowered)):
                continue
            terms = _evidence_terms(window)
            # For personal expectations, every material word must be present:
            # overlap alone can mistake a different person or child as a match.
            if "expect" in actions and not claim_terms <= terms:
                continue
            minimum_overlap = 2 if claim_numbers else 3
            if not actions <= terms or len(claim_terms & terms) < max(minimum_overlap, (len(claim_terms) * 3 + 3) // 4):
                continue
            if actor_terms and not actor_terms <= terms:
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
            if (not re.search(r"\b(?:will|plans? to|proposes? to|aims? to|expected to|set to)\b", claim_text, re.I)
                    and re.search(r"\b(?:will|plans? to|proposes? to|proposal|proposed|aims? to|expected to|set to)\b", action_context, re.I)):
                continue
            if not claim_qualifiers <= window_qualifiers:
                continue
            if not claim_qualifiers and window_qualifiers & {"umano", "alleged", "allegedly", "reportedly"}:
                continue
            if not claim_qualifiers and _negates_material_action(action_words, actions):
                continue
            if best_window is None or len(window) < len(best_window):
                best_window = window
    if best_window is not None:
        return "supports", best_window
    return "related", "The readable article did not establish every material action, person, place, date, number and qualification in the claim."


def _article_relation(claim: str, body: str, *, allow_nli: bool = True) -> tuple[str, str]:
    """Require a direct prose assertion, including all numbers and qualifiers."""
    claim_words = _words(claim)
    if len(claim_words) < 5 or len(claim_words) > 90:
        return "related", "The claim cannot be checked by the strict assertion gate."
    phrase = " ".join(claim_words)
    for sentence in _sentences(body):
        if len(sentence) > 1600:
            continue
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
            return "contradicts", sentence
        # Mentioning an exact claim inside a question, hypothetical or embedded
        # quotation does not assert that it happened. Keep these as reading only.
        if prefix:
            continue
        material_qualifiers = {"umano", "alleged", "allegedly", "suspected", "reportedly", "hindi", "not", "no", "never"}
        if (set(sentence_words) & material_qualifiers) != (set(claim_words) & material_qualifiers):
            continue
        if any(re.search(r"\b" + cue + r"\b", joined) for cue in ("false", "fake", "misleading", "untrue", "incorrect", "debunked", "mali", "peke", "huwad")):
            continue
        return "supports", sentence
    relationship, passage = _material_support(claim, body)
    if relationship == "supports" or not allow_nli:
        return relationship, passage
    return local_nli.assess_relation(claim, body)


def _headline_has_body_corroboration(claim: str, title: str, body: str) -> bool:
    headline_relation, _ = _article_relation(claim, title, allow_nli=False)
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


def _assess_readable_claim(claim: str, body: str) -> tuple[str, str]:
    """Check every stated sentence and detect opposed assertions in one article.

    This remains a bounded lexical gate, not a general truth/entailment model.
    Unmatched parts of a multi-sentence post prevent a support override.
    """
    claim_parts = _sentences(claim)
    if not claim_parts:
        return "unverified", "No claim text was supplied."
    relations = []
    passages = []
    opposing_passages = []
    for part in claim_parts:
        relationship, passage = _article_relation(part, body)
        observed = {relationship}
        # Do not let an early assertion hide an explicit correction later on.
        for sentence in _sentences(body):
            sentence_relation, _ = _article_relation(part, sentence, allow_nli=False)
            if sentence_relation in {"supports", "contradicts"}:
                observed.add(sentence_relation)
        if relationship == 'supports' and re.search(
            r"\b(?:this|that|the)\s+(?:claim|statement|report)\s+(?:is|was)\s+(?:false|fake|incorrect|misleading|not\s+true)\b",
            body, re.I,
        ):
            return 'conflicting', 'The article repeats an assertion but also explicitly describes the claim as false or misleading.'
        if {"supports", "contradicts"} <= observed:
            return "conflicting", "The article contains both supporting and opposing assertions for the same claim."
        relations.append(relationship)
        if relationship in {"supports", "contradicts"}:
            passages.append(passage)
        if relationship == "contradicts":
            opposing_passages.append(passage)
    if "contradicts" in relations:
        return "contradicts", "\n".join(dict.fromkeys(opposing_passages))
    if all(relationship == "supports" for relationship in relations):
        return "supports", "\n".join(dict.fromkeys(passages))
    return "related", "The readable article did not establish every statement in the submitted text."


def _direct_photo_reports(assessments, sources, claim, reader):
    # An original dated photo report can be primary evidence for the event it
    # actually describes. This does not make other articles primary authority.
    if reader.get('status')!='assessed':return []
    by_url={source.get('url'):source for source in sources}
    matches=[]
    dates=_explicit_event_dates(claim)
    if not dates:return []
    for item in assessments:
        source=by_url.get(item.get('url'),{})
        if (source.get('content_kind')=='publisher_photo_report'
                and source.get('provenance_verified') is True
                and source.get('photo_credit') and source.get('date_published')
                and _is_trusted_source(item.get('url'))
                and item.get('relationship')=='supports' and item.get('decision_eligible')
                and dates <= _explicit_event_dates(item.get('evidence_excerpt',''))):
            matches.append(item)
    return matches


def apply_evidence(model_prediction: dict, related_sources: list[dict], fact_check_matches: list[dict], claim: str = "") -> dict:
    # Only article text supplied by the reader is eligible; no external inference.
    reader = local_nli.health()
    reader["model_status"] = reader["status"]
    reader["status"] = "assessed" if any(s.get("content_status") == "readable" and s.get("article_text") for s in related_sources) else "no_readable_sources"
    assessments = []
    for source in related_sources:
        body = source.get("article_text", "") if source.get("content_status") == "readable" else ""
        relationship, reason = _assess_readable_claim(claim, body) if body and claim else ("unverified", "The full article could not be assessed.")
        excerpt = reason if relationship in {"supports", "contradicts"} else ""
        # A locally supplied passage must be an actual article substring (or a
        # concatenation of complete checked sentences), never invented text.
        eligible = bool(excerpt) and all(" ".join(part.split()) in " ".join(body.split()) for part in excerpt.splitlines())
        validation_issues = []
        reason_tl = ""
        if eligible:
            clean_claim = _without_post_metadata_dates(claim)
            clean_claim = re.sub(r"\s*\|\s*via\s+[A-Z][\w.-]*(?:\s+[A-Z][\w.-]*){0,3}(?:,\s*[A-Z][\w.& -]{1,60})?\s*$", "", clean_claim)
            checks = [('person', _person_entity_anchors(clean_claim) <= _person_entity_anchors(excerpt)
                       and all(name in ' '.join(_words(excerpt)) for name in _named_actor_anchors(clean_claim)))]
            if relationship == 'supports':
                checks.extend([
                    ('quantity', _material_numbers(clean_claim) <= _material_numbers(excerpt)),
                    ('amount', _peso_amounts(clean_claim) <= _peso_amounts(excerpt)),
                    ('event_date', _explicit_event_dates(clean_claim) <= _explicit_event_dates(excerpt)),
                    ('event_year', _explicit_event_years(clean_claim) <= _explicit_event_years(excerpt)),
                    ('location', _material_locations(clean_claim) <= _material_locations(excerpt)),
                ])
            else:
                # Different events/dates alone are not a debunk of this event.
                checks.extend([('event_date', _explicit_event_dates(clean_claim) <= _explicit_event_dates(excerpt)),
                               ('event_year', _explicit_event_years(clean_claim) <= _explicit_event_years(excerpt))])
            validation_issues = [key for key, ok in checks if not ok]
            if validation_issues:
                eligible = False
                relationship = 'related'
                reason = 'The passage did not preserve the material anchors: ' + ', '.join(validation_issues) + '.'
        # Relative dates need a resolved post-time comparison. Do not treat
        # "next week" in an undated/older article as the same real event.
        if re.search(r"\b(?:today|tomorrow|yesterday|tonight|(?:next|last|this|coming)\s+(?:week|month|year)|bukas|kahapon|ngayon|mamaya)\b", claim, re.I):
            eligible = False
            reason = "Relative event timing has not been aligned with the post date; this source cannot change the label."
        if (relationship == "related" and body and claim
                and _headline_has_body_corroboration(claim, source.get("title", ""), body)):
            relationship = "supports"
            reason = "The publisher headline states the complete claim, and the readable article body corroborates its material details."
            # Headline/body term overlap may help readers find context, but does
            # not provide a direct body passage proving all claim details.
            eligible = False
        assessments.append({"url": source.get("url"), "relationship": relationship, "reason": reason,
                            "evidence_excerpt": excerpt, "decision_eligible": eligible,
                            "reason_tl": reason_tl, "validation_issues": validation_issues})
    # Loading may have occurred during fallback inference; report its final state.
    current_reader = local_nli.health()
    reader["model_status"] = current_reader["status"]
    reader["loaded"] = current_reader["loaded"]
    supports = [item for item in assessments if item["relationship"] == "supports" and item["decision_eligible"]]
    contradicts = [item for item in assessments if item["relationship"] == "contradicts" and item["decision_eligible"]]
    independent_supports = _independent_trusted_sources(supports, related_sources)
    independent_contradictions = _independent_trusted_sources(contradicts, related_sources)
    credible_supports = [
        item for item in supports if _is_trusted_source(item.get("url"))
    ]
    credible_contradictions = [
        item for item in contradicts if _is_trusted_source(item.get("url"))
    ]
    conflicted_articles = [item for item in assessments if item['relationship'] == 'conflicting' and _is_trusted_source(item.get('url'))]
    primary_supports = [item for item in credible_supports if _primary_authority_for_claim(item.get('url'), claim)]
    primary_contradictions = [item for item in credible_contradictions if _primary_authority_for_claim(item.get('url'), claim)]
    photo_supports = _direct_photo_reports(credible_supports, related_sources, claim, reader)
    sufficient_support = (bool(primary_supports) or bool(photo_supports) or len(independent_supports) >= 2) and not credible_contradictions and not conflicted_articles
    sufficient_contradiction = (bool(primary_contradictions) or len(independent_contradictions) >= 2) and not credible_supports and not conflicted_articles
    semantic_trial = config.EVIDENCE_POLICY == 'semantic_single_source_trial' and reader.get('status') == 'assessed'
    trial_supports = credible_supports if semantic_trial and not credible_contradictions and not conflicted_articles else []
    trial_contradictions = credible_contradictions if semantic_trial and not credible_supports and not conflicted_articles else []
    sufficient_support = sufficient_support or bool(trial_supports)
    sufficient_contradiction = sufficient_contradiction or bool(trial_contradictions)
    evidence_rule = 'model_fallback'
    if sufficient_support:
        label, internal, relationship = "No Misleading Information Detected", "Non-Misleading", "supports"
        chosen = primary_supports or photo_supports or (independent_supports if len(independent_supports) >= 2 else trial_supports)
        evidence_rule = 'scoped_primary_authority' if primary_supports else 'direct_publisher_photo_report' if photo_supports else 'two_independent_publishers' if len(independent_supports) >= 2 else 'validated_single_source_trial'
        basis = ("A readable primary authority within its subject scope directly supports the complete claim and its material details, with no readable trusted contradiction."
                 if primary_supports else "A readable original publisher photo report with verified page provenance and a named photo credit supports the complete dated event, with no readable trusted contradiction." if photo_supports else "Two independent readable trusted publishers directly support the complete claim and its material details, with no readable trusted source directly contradicting it.")
        if evidence_rule == 'validated_single_source_trial':
            basis = 'Local semantic trial: a readable trusted article supports the complete claim using server-owned passages, with no eligible trusted contradiction. This is not independently verified real-world accuracy.'
    elif sufficient_contradiction:
        label, internal, relationship = "Potentially Misleading", "Misleading", "contradicts"
        chosen = primary_contradictions or (independent_contradictions if len(independent_contradictions) >= 2 else trial_contradictions)
        evidence_rule = 'scoped_primary_authority' if primary_contradictions else 'two_independent_publishers' if len(independent_contradictions) >= 2 else 'validated_single_source_trial'
        basis = ("A readable primary authority within its subject scope directly contradicts the claim, with no readable trusted support."
                 if primary_contradictions else "Two independent readable trusted publishers directly contradict the complete claim, with no readable trusted source supporting it.")
        if evidence_rule == 'validated_single_source_trial':
            basis = 'Local semantic trial: a readable trusted article contradicts the complete claim using server-owned passages, with no eligible trusted support. This is not independently verified real-world accuracy.'
    else:
        label, internal = model_prediction["public_label"], model_prediction["internal_label"]
        relationship = (
            "conflicting" if conflicted_articles or (credible_supports and credible_contradictions)
            else "supports" if any(item['relationship'] == 'supports' and _is_trusted_source(item.get('url')) for item in assessments)
            else "contradicts" if any(item['relationship'] == 'contradicts' and _is_trusted_source(item.get('url')) for item in assessments)
            else "related" if any(item["relationship"] == "related" for item in assessments)
            else "unverified" if assessments or fact_check_matches
            else "not_assessed"
        )
        basis = "Not independently verified. Available evidence is insufficient or conflicting; the final label follows the original hybrid prediction. A missing source is not evidence that a claim is false."
        chosen = []
    return {
        "internal_label": internal, "public_label": label,
        "decision_source": "verified_evidence" if chosen else "screening_model",
        "decision_basis": basis, "evidence_relationship": relationship,
        "evidence_rule": evidence_rule, "evidence_policy": config.EVIDENCE_POLICY,
        "evidence_reader": {key: value for key, value in reader.items() if key != "assessments"},
        "evidence_explanation_en": " ".join(dict.fromkeys(item["reason"] for item in chosen))[:1500],
        "evidence_explanation_tl": " ".join(dict.fromkeys(item.get("reason_tl", "") for item in chosen))[:1500],
        "supporting_source_count": len(credible_supports), "strong_fact_check_matches": [],
        "evidence_assessments": assessments,
        "evidence_urls": [item["url"] for item in chosen],
        "evidence_adjusted": label != model_prediction["public_label"],
    }
