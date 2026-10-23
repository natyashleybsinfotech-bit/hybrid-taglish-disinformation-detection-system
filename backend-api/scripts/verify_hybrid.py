"""Read-only raw-text parity check for the one explicitly selected model profile.

This script never fits, selects, tunes, or reads cached embeddings. Candidate
records are joined to saved predictions only by the SHA-256 of supplied text.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import numpy as np
from src.model_runtime import runtime, sha256

ATOL = 1e-5
RTOL = 1e-5


def _read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _candidate_records():
    references = _read_csv(runtime.root / "records" / "test_predictions.csv")
    reference_by_id = {row["record_id"]: row for row in references}
    full_rows = _read_csv(runtime.root / "records" / "full_text_label.csv")
    rows_by_id = {
        hashlib.sha256(row["text"].encode("utf-8")).hexdigest(): row
        for row in full_rows
    }
    missing = sorted(set(reference_by_id) - set(rows_by_id))
    if missing:
        raise AssertionError(f"{len(missing)} saved prediction IDs have no exact raw-text match")
    rows = [(record_id, rows_by_id[record_id], reference_by_id[record_id]) for record_id in reference_by_id]
    return rows, "p_misleading", "prediction", {
        "full_text_label.csv": sha256(runtime.root / "records" / "full_text_label.csv"),
        "partitions.csv": sha256(runtime.root / "records" / "partitions.csv"),
        "test_predictions.csv": sha256(runtime.root / "records" / "test_predictions.csv"),
    }


def _legacy_records():
    rows = _read_csv(runtime.root / "records" / "test.csv")
    references = _read_csv(runtime.root / "records" / "test_predictions.csv")
    reference_by_id = {row["record_id"]: row for row in references}
    joined = []
    for row in rows:
        record_id = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        joined.append((record_id, row, reference_by_id[record_id]))
    return joined, "model_4_p_misleading", "model_4_prediction", {
        "test.csv": sha256(runtime.root / "records" / "test.csv"),
        "test_predictions.csv": sha256(runtime.root / "records" / "test_predictions.csv"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=BASE.parent / "tmp/hybrid-verification.json")
    parser.add_argument("--limit", type=int, default=0, help="Diagnostic subset only; zero verifies every saved test record.")
    args = parser.parse_args()
    started = time.perf_counter()
    health = runtime.initialize()
    print(json.dumps(health), flush=True)
    if not health["ready"]:
        raise SystemExit("Model failed to initialize; no prediction comparison was run")

    if runtime.profile["metadata_kind"] == "candidate_results":
        rows, score_column, label_column, source_hashes = _candidate_records()
    else:
        rows, score_column, label_column, source_hashes = _legacy_records()
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        raise AssertionError("No exact raw-text records were available for verification")

    details = []
    scores = []
    expected_scores = []
    false_positive_ids = []
    false_negative_ids = []
    multichunk = 0
    for start in range(0, len(rows), 16):
        batch = rows[start:start + 16]
        predictions = runtime.predict_many([row[1]["text"] for row in batch])
        for prediction, (record_id, raw, expected) in zip(predictions, batch):
            score = prediction.model_score
            expected_score = float(expected[score_column])
            expected_label = int(expected[label_column])
            actual_source_label = int(raw["label"])
            if "true_inherited_label" in expected and int(expected["true_inherited_label"]) != actual_source_label:
                raise AssertionError(f"Inherited label mismatch for {record_id}")
            score_matches = bool(np.isclose(score, expected_score, atol=ATOL, rtol=RTOL))
            label_matches = prediction.predicted_class == expected_label
            if not score_matches or not label_matches:
                details.append({
                    "record_id": record_id, "actual_score": score,
                    "reference_score": expected_score,
                    "actual_label": prediction.predicted_class,
                    "reference_label": expected_label,
                })
            if actual_source_label == 0 and expected_label == 1:
                false_positive_ids.append(record_id)
            if actual_source_label == 1 and expected_label == 0:
                false_negative_ids.append(record_id)
            scores.append(score)
            expected_scores.append(expected_score)
            multichunk += int(prediction.chunk_count > 1)
        if start == 0 or (start + len(batch)) % 160 == 0 or start + len(batch) == len(rows):
            print(f"Raw-text comparison: {start + len(batch)}/{len(rows)}", flush=True)

    delta = np.abs(np.asarray(scores) - np.asarray(expected_scores))
    probability_mismatches = int((~np.isclose(scores, expected_scores, atol=ATOL, rtol=RTOL)).sum())
    label_mismatches = sum(item["actual_label"] != item["reference_label"] for item in details)
    result = {
        "training_run_id": runtime.profile_id,
        "model": health,
        "raw_text_records": len(rows),
        "all_saved_test_records_checked": not args.limit,
        "reference_files_sha256": source_hashes,
        "atol": ATOL,
        "rtol": RTOL,
        "tolerance_rule": "abs(actual-reference) <= 1e-5 + 1e-5*abs(reference)",
        "max_absolute_probability_error": float(delta.max()),
        "mean_absolute_probability_error": float(delta.mean()),
        "probability_mismatches": probability_mismatches,
        "label_mismatches": int(label_mismatches),
        "multi_chunk_records": multichunk,
        "saved_reference_false_positives": len(false_positive_ids),
        "saved_reference_false_negatives": len(false_negative_ids),
        "false_positive_example_ids": false_positive_ids[:3],
        "false_negative_example_ids": false_negative_ids[:3],
        "elapsed_seconds": time.perf_counter() - started,
        "details": details,
        "used_cached_embeddings": False,
        "training_or_tuning_performed": False,
    }
    result["passed"] = probability_mismatches == label_mismatches == 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
