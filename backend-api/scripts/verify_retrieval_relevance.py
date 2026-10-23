"""Verify the supplied retrieval false match locally without exporting the caption."""

import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from src import retrieval
from src.model_runtime import PROFILES


def main():
    candidate_root = BASE / PROFILES["full-cleaned-20261023T022416Z"]["artifact_directory"]
    fixture = candidate_root / "verification/candidate_regression_cases.json"
    if not fixture.is_file():
        raise SystemExit("The ignored local candidate regression fixture is missing")
    cases = json.loads(fixture.read_text(encoding="utf-8"))
    query = next(case["text"] for case in cases if case["name"] == "caption_without_dom_control")
    false_match = {
        "title": "Juan dela Cruz: Kael, patuloy na hinanap ang vigilante | Episode 21",
        "link": "https://www.abs-cbn.com/videos/juan-dela-cruz-kael-patuloy-na-hinanap-ang-vigilante-episode-21-338706",
        "snippet": "Watch highlights from the favorite Kapamilya teleserye episode.",
    }
    relevant, score = retrieval._is_relevant(false_match, retrieval._informative_terms(query), query)
    if relevant:
        raise SystemExit("The supplied fictional episode still passes the relevance gate")

    report = {
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "synthetic_false_match_rejected": True,
        "synthetic_term_overlap_score_before_alignment_gate": score,
        "rule": "Reject episodic entertainment for non-entertainment queries and require complete conservative person-name alignment when those anchors exist.",
        "exact_caption_sent_to_external_provider": False,
        "live_provider_health_evidence": "See PROVIDER-VERIFICATION.json; it uses a neutral synthetic query.",
        "classification_invoked": False,
    }
    output = BASE.parent / "docs/RETRIEVAL-RELEVANCE-VERIFICATION.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
