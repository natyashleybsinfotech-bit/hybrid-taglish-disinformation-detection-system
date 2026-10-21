"""Read-only model_4 diagnostic for saved test counts and direct/API parity.

This script never trains, tunes, changes the threshold, or stores raw input text.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from src.model_runtime import prepare_text, runtime


def post_json(url: str, payload: dict) -> dict:
    request = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=180) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=BASE.parent / "docs/PREDICTION-PATH-DIAGNOSTIC.json")
    args = parser.parse_args()
    records = runtime.root / "records"
    with (records / "test.csv").open(encoding="utf-8-sig", newline="") as stream:
        raw = list(csv.DictReader(stream))
    with (records / "test_predictions.csv").open(encoding="utf-8-sig", newline="") as stream:
        references = {row["record_id"]: row for row in csv.DictReader(stream)}

    pairs = []
    for row in raw:
        record_id = hashlib.sha256(row["text"].encode()).hexdigest()
        pairs.append((row, record_id, references[record_id]))
    truth = [int(row["label"] == "Misleading") for row, _, _ in pairs]
    predicted = [int(reference["model_4_prediction"]) for _, _, reference in pairs]
    tn = sum(t == 0 and p == 0 for t, p in zip(truth, predicted))
    fp = sum(t == 0 and p == 1 for t, p in zip(truth, predicted))
    fn = sum(t == 1 and p == 0 for t, p in zip(truth, predicted))
    tp = sum(t == 1 and p == 1 for t, p in zip(truth, predicted))
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1_pos = 2 * precision * recall / (precision + recall)
    precision_neg = tn / (tn + fn)
    recall_neg = tn / (tn + fp)
    f1_neg = 2 * precision_neg * recall_neg / (precision_neg + recall_neg)

    health = runtime.initialize()
    if not health["ready"]:
        raise SystemExit(health["error"])
    selected = [next(pair for pair in pairs if int(pair[2]["model_4_prediction"]) == target) for target in (0, 1)]
    path_checks = []
    for row, record_id, reference in selected:
        direct = runtime.predict(row["text"]).to_dict()
        api = post_json(args.api.rstrip("/") + "/analyze", {"text": row["text"], "retrieve_sources": False})
        reference_score = float(reference["model_4_p_misleading"])
        path_checks.append({
            "record_id": record_id,
            "ground_truth": row["label"],
            "reference_prediction": int(reference["model_4_prediction"]),
            "direct_prediction": direct["predicted_class"],
            "api_prediction": api["predicted_class"],
            "reference_p_misleading": reference_score,
            "direct_p_misleading": direct["model_score"],
            "api_p_misleading": api["model_score"],
            "direct_reference_absolute_error": abs(direct["model_score"] - reference_score),
            "api_direct_absolute_error": abs(api["model_score"] - direct["model_score"]),
            "api_analyzed_expected_prepared_text": api["analyzed_text"] == prepare_text(row["text"]),
            "api_feature_count": len(api["linguistic_indicators"]),
            "public_label": api["public_label"],
            "displayed_class_score": api["displayed_class_score"],
        })

    result = {
        "purpose": "Read-only integration diagnostic; no training, tuning, threshold change, or raw-text logging.",
        "dataset": {"full": 4000, "train": 2800, "validation": 602, "test": len(pairs)},
        "saved_test_result": {
            "ground_truth": {"Non-Misleading": truth.count(0), "Misleading": truth.count(1)},
            "predictions": {"Non-Misleading": predicted.count(0), "Misleading": predicted.count(1)},
            "confusion": {"TN": tn, "FP": fp, "FN": fn, "TP": tp},
            "correct": tn + tp,
            "accuracy": (tn + tp) / len(pairs),
            "macro_f1": (f1_neg + f1_pos) / 2,
        },
        "model": {key: health[key] for key in ("classifier", "training_run_id", "sha256", "device", "decision_threshold", "label_mapping")},
        "path_checks": path_checks,
        "interpretation": {
            "reference_parity": "Matching saved probabilities proves reproduction of the recorded model_4 pipeline; it is not classification accuracy.",
            "accuracy": "560/598 compares predictions with saved ground-truth labels.",
            "remaining_hypothesis": "Repeated Misleading outputs for short Facebook-style inputs can be model domain shift or dataset-source bias after extraction and path defects are excluded.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
