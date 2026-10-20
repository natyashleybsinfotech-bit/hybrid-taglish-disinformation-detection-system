"""Read-only integration comparison. Never fits, selects or tunes any model.

Reads raw test.csv texts and joins references by SHA-256 record_id. Does not read
cached embeddings, train/validation texts, or alternative classifier artifacts.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import time
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import numpy as np
from src.model_runtime import runtime, sha256, RUN_ID

ATOL = 1e-5
RTOL = 1e-5


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE.parent / "tmp/hybrid-verification.json")
    args = parser.parse_args()
    started = time.perf_counter()
    health = runtime.initialize()
    print(json.dumps(health), flush=True)
    if not health["ready"]:
        raise SystemExit("Model failed to initialize; no prediction comparison was run")
    raw_path = runtime.root / "records" / "test.csv"
    reference_path = runtime.root / "records" / "test_predictions.csv"
    selection_path = runtime.root / "records" / "selected_configurations.csv"
    manifest = json.loads((runtime.root / "run_manifest.json").read_text(encoding="utf-8"))
    assert sha256(selection_path) == manifest["selection_sha256"], "Saved selection checksum mismatch"
    with raw_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    with reference_path.open(encoding="utf-8-sig", newline="") as stream:
        references = list(csv.DictReader(stream))
    with selection_path.open(encoding="utf-8-sig", newline="") as stream:
        selections = [row for row in csv.DictReader(stream) if row["model"] == health["name"]]
    assert len(selections) == 1 and float(selections[0]["threshold"]) == 0.65
    reference_by_id = {row["record_id"]: row for row in references}
    ids = [hashlib.sha256(row["text"].encode("utf-8")).hexdigest() for row in rows]
    assert len(reference_by_id) == len(references) == len(rows) == 598
    assert len(set(ids)) == len(rows) and set(ids) == set(reference_by_id)
    details, all_scores, all_expected, label_mismatches, multichunk = [], [], [], [], 0
    for start in range(0, len(rows), 16):
        predictions = runtime.predict_many([row["text"] for row in rows[start:start + 16]])
        for offset, prediction in enumerate(predictions):
            record_id = ids[start + offset]
            expected = reference_by_id[record_id]
            score = prediction.model_score
            reference_score = float(expected["model_4_p_misleading"])
            reference_label = int(expected["model_4_prediction"])
            matches_score = bool(np.isclose(score, reference_score, atol=ATOL, rtol=RTOL))
            matches_label = prediction.predicted_class == reference_label
            if not matches_label:
                label_mismatches.append(record_id)
            if not matches_label or not matches_score:
                details.append(dict(record_id=record_id, actual_score=score, reference_score=reference_score,
                    actual_label=prediction.predicted_class, reference_label=reference_label))
            all_scores.append(score)
            all_expected.append(reference_score)
            multichunk += int(prediction.chunk_count > 1)
        print(f"Raw-text comparison: {min(start + 16, len(rows))}/{len(rows)}", flush=True)
    delta = np.abs(np.asarray(all_scores) - np.asarray(all_expected))
    result = {
        "training_run_id": RUN_ID, "model": health, "raw_text_records": len(rows),
        "reference_files_sha256": {"test.csv": sha256(raw_path), "test_predictions.csv": sha256(reference_path), "selected_configurations.csv": sha256(selection_path)},
        "atol": ATOL, "rtol": RTOL, "tolerance_rule": "abs(actual-reference) <= 1e-5 + 1e-5*abs(reference)",
        "max_absolute_probability_error": float(delta.max()), "mean_absolute_probability_error": float(delta.mean()),
        "probability_mismatches": int((~np.isclose(all_scores, all_expected, atol=ATOL, rtol=RTOL)).sum()),
        "label_mismatches": len(label_mismatches), "multi_chunk_records": multichunk,
        "elapsed_seconds": time.perf_counter() - started,
        "details": details, "used_cached_embeddings": False, "training_or_tuning_performed": False,
    }
    result["passed"] = result["probability_mismatches"] == result["label_mismatches"] == 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
