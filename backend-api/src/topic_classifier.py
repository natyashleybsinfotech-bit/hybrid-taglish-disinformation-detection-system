"""Lightweight, explainable routing into the paper-defined topic domains.

Topic is dataset metadata, not the misinformation prediction target.  This
router deliberately produces a suggestion that remains subject to human
review in the administrator workflow.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

try:
    from .. import config
except ImportError:  # Legacy test runner adds backend-api/src to sys.path.
    import config


TOPIC_TERMS: dict[str, tuple[str, ...]] = {
    "Politics, Governance, and Elections": (
        "politics", "political", "government", "governance", "election", "elections",
        "president", "vice president", "senate", "senator", "congress", "congressman",
        "mayor", "governor", "barangay", "comelec", "administration", "legislation",
        "batas", "gobyerno", "halalan", "eleksyon", "pangulo", "senado", "senador",
        "politika", "opisyal", "kandidato",
    ),
    "Health and Medicine": (
        "health", "medicine", "medical", "doctor", "hospital", "disease", "virus",
        "vaccine", "vaccination", "covid", "symptom", "treatment", "patient", "drug",
        "gamot", "sakit", "bakuna", "kalusugan", "doktor", "ospital", "pasyente",
        "lunas", "nutrisyon",
    ),
    "Economy, Finance, and Employment": (
        "economy", "economic", "finance", "financial", "inflation", "peso", "bank",
        "tax", "employment", "unemployment", "job", "salary", "wage", "business",
        "investment", "market", "price", "economiya", "pananalapi", "trabaho", "sahod",
        "presyo", "negosyo", "bangko", "buwis", "manggagawa",
    ),
    "Public Safety, Disaster, and Security": (
        "public safety", "disaster", "security", "police", "crime", "criminal", "military",
        "typhoon", "storm", "earthquake", "flood", "fire", "accident", "emergency",
        "rescue", "bagyo", "lindol", "baha", "sunog", "sakuna", "krimen", "pulis",
        "sundalo", "aksidente", "kaligtasan", "seguridad",
    ),
    "Science, Technology, and Environment": (
        "science", "scientific", "technology", "artificial intelligence", "internet",
        "software", "computer", "cyber", "research", "climate", "environment", "pollution",
        "weather", "energy", "space", "agham", "teknolohiya", "kalikasan", "klima",
        "pananaliksik", "kompyuter", "kapaligiran",
    ),
    "Education and Social Issues": (
        "education", "school", "student", "teacher", "university", "college", "classroom",
        "poverty", "human rights", "gender", "housing", "inequality", "welfare", "tuition",
        "edukasyon", "paaralan", "estudyante", "mag-aaral", "guro", "kolehiyo",
        "kahirapan", "karapatan", "lipunan",
    ),
    "Entertainment and Public Figures": (
        "entertainment", "celebrity", "actor", "actress", "singer", "movie", "film",
        "television", "showbiz", "influencer", "concert", "artist", "music", "pageant",
        "artista", "pelikula", "teleserye", "mang-aawit", "konsiyerto", "awit",
    ),
}


@dataclass(frozen=True)
class TopicSuggestion:
    topic: str
    confidence: float
    matched_terms: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "topic": self.topic,
            "confidence": self.confidence,
            "matched_terms": list(self.matched_terms),
            "review_status": "auto_suggested",
        }


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9-]+", " ", value).strip()


def suggest_topic(text: str) -> TopicSuggestion:
    """Return one paper-defined topic and an intentionally conservative score."""

    normalized = f" {_normalized(text)} "
    scores: dict[str, int] = {}
    matches: dict[str, list[str]] = {}
    for topic, terms in TOPIC_TERMS.items():
        found: list[str] = []
        score = 0
        for term in terms:
            token = _normalized(term)
            if re.search(rf"(?<![a-z0-9-]){re.escape(token)}(?![a-z0-9-])", normalized):
                found.append(term)
                score += 2 if " " in token else 1
        scores[topic] = score
        matches[topic] = found

    ranked = sorted(scores, key=lambda topic: (-scores[topic], config.TOPIC_CATEGORIES.index(topic)))
    best = ranked[0]
    best_score = scores[best]
    if best_score == 0:
        return TopicSuggestion("Other and General", 0.35, ())

    second_score = scores[ranked[1]]
    total = sum(scores.values())
    dominance = best_score / max(total, 1)
    margin = (best_score - second_score) / max(best_score, 1)
    confidence = min(0.95, 0.50 + (0.25 * dominance) + (0.20 * margin))
    return TopicSuggestion(best, round(confidence, 4), tuple(matches[best][:8]))
