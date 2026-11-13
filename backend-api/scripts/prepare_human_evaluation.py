"""Freeze a private, stratified review batch from the candidate's held-out test split.

The inherited labels are sampling strata only, never human ground truth. Raw texts
remain under ignored research-data; the committed manifest contains hashes only.
"""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
ARTIFACT = BASE / "backend-api/models/local-trials/full-cleaned-20261023T022416Z"
PRIVATE = BASE / "research-data/evaluation-20261029"
MANIFEST = BASE / "docs/research/EVALUATION-BATCH-MANIFEST.json"


def read_rows(name):
    with (ARTIFACT / "records" / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def length_band(text):
    words = len(text.split())
    return "under_50" if words < 50 else "50_to_199" if words < 200 else "200_plus"


def main():
    if PRIVATE.exists() or MANIFEST.exists():
        raise SystemExit("The frozen evaluation batch already exists; refusing to replace it.")
    texts = {hashlib.sha256(row["text"].encode("utf-8")).hexdigest(): row for row in read_rows("full_text_label.csv")}
    partitions = {row["record_id"]: row for row in read_rows("partitions.csv")}
    predictions = {row["record_id"]: row for row in read_rows("test_predictions.csv")}
    assert set(predictions) <= set(texts) & set(partitions)
    groups = {}
    for row in partitions.values():
        groups.setdefault(row["claim_group_id"], set()).add(row["split"])
    if any(len(splits) != 1 for splits in groups.values()):
        raise ValueError("Claim-group overlap across training, validation and test splits")
    if any(partitions[record_id]["split"] != "test" for record_id in predictions):
        raise ValueError("Prediction record outside the held-out test split")
    diagnostic_file = ARTIFACT / "verification/candidate_regression_cases.json"
    diagnostic_ids = {hashlib.sha256(item["text"].encode("utf-8")).hexdigest() for item in json.loads(diagnostic_file.read_text(encoding="utf-8"))}
    strata = {(label, band): [] for label in ("0", "1") for band in ("under_50", "50_to_199", "200_plus")}
    for record_id, predicted in predictions.items():
        if record_id in diagnostic_ids:
            continue
        source = texts[record_id]
        assert source["label"] == predicted["true_inherited_label"]
        strata[(source["label"], length_band(source["text"]))].append(record_id)
    selected = []
    for (label, band), ids in strata.items():
        # Stable hash ordering freezes selection independently of CSV row order.
        ordered = sorted(ids, key=lambda value: hashlib.sha256(("suriph-human-eval-v1:" + value).encode()).hexdigest())
        if len(ordered) < 4:
            raise ValueError(f"Insufficient held-out cases for {label}/{band}")
        selected.extend(ordered[:4])
    if len({partitions[item]["claim_group_id"] for item in selected}) != len(selected):
        raise ValueError("Duplicate claim group in evaluation batch")
    PRIVATE.mkdir(parents=True)
    fields = ["case_id", "mode", "text", "record_id", "claim_group_id", "source_csv_row", "inherited_label_for_sampling_only", "saved_model_score_for_replay_only", "evidence_url", "human_label", "reviewer_1", "reviewer_2", "adjudication_notes", "claim_date", "claim_location", "source_provenance", "review_status"]
    with (PRIVATE / "review_batch.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for index, record_id in enumerate(selected, 1):
            writer.writerow({"case_id": f"S{index:03}", "mode": "text", "text": texts[record_id]["text"], "record_id": record_id, "claim_group_id": partitions[record_id]["claim_group_id"], "source_csv_row": partitions[record_id]["source_csv_row"], "inherited_label_for_sampling_only": texts[record_id]["label"], "saved_model_score_for_replay_only": predictions[record_id]["p_misleading"], "review_status": "pending_human_review"})
    source_hashes = {name: hashlib.sha256((ARTIFACT / "records" / name).read_bytes()).hexdigest() for name in ("full_text_label.csv", "partitions.csv", "test_predictions.csv")}
    manifest = {"batch_id": "suriph-human-eval-v1-20261029", "model_run": "full-cleaned-20261023T022416Z", "selection": "Four deterministic held-out records per inherited-label/length stratum; inherited labels are not ground truth", "text_cases": 24, "media_cases": 0, "training_or_validation_claim_group_overlap": 0, "diagnostic_case_overlap": 0, "source_file_sha256": source_hashes, "record_ids": selected, "private_review_file": "research-data/evaluation-20261029/review_batch.csv", "human_judgments_recorded": 0, "ready_for_accuracy_claim": False}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"batch": manifest["batch_id"], "cases": 24, "strata": {f"{label}/{band}": 4 for label, band in strata}, "claim_group_overlap": 0, "diagnostic_overlap": 0}))


if __name__ == "__main__":
    main()
