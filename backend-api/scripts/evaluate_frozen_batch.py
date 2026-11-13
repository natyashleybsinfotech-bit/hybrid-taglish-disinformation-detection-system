"""Replay the frozen private batch through the final HTTP output and score reviewed cases.

Run against the same local candidate API used by the study. No inherited label is
treated as ground truth. Unresolved claims and failed requests remain in the report.
"""

import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "research-data/evaluation-20261029/review_batch.csv"
OUTPUT = ROOT / "research-data/evaluation-20261029/end_to_end_results.json"
BASE = os.environ.get("SURI_EVAL_API_URL", "http://127.0.0.1:8000").rstrip("/")


def main():
    with BATCH.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 24 or len({row["record_id"] for row in rows}) != 24:
        raise ValueError("Frozen batch is missing or altered")
    if sys.argv[1:] == ["--audit"]:
        print(json.dumps({"total_cases": len(rows), "adjudicated_with_evidence": sum(row["review_status"] == "adjudicated" and row["human_label"] in ("Misleading", "Non-Misleading") and bool(row["evidence_url"]) for row in rows), "unresolved_or_pending": sum(row["review_status"] != "adjudicated" for row in rows), "network_requests": 0}))
        return
    if not any(row["review_status"] == "adjudicated" for row in rows):
        raise SystemExit("Human adjudication is still pending; use --audit to inspect preparation without transmitting case text to the provider")
    results = []
    with httpx.Client(timeout=180) as client:
        ready = client.get(BASE + "/ready").json()
        if not ready.get("ready") or ready["model"].get("training_run_id") != "full-cleaned-20261023T022416Z":
            raise ValueError("The intended candidate runtime is not ready")
        for row in rows:
            outcome = {"case_id": row["case_id"], "record_id": row["record_id"], "review_status": row["review_status"], "human_label": row["human_label"] or None, "evidence_url_recorded": bool(row["evidence_url"])}
            try:
                response = client.post(BASE + "/analyze", json={"text": row["text"], "retrieve_sources": True})
                outcome["http_status"] = response.status_code
                if response.status_code == 200:
                    body = response.json()
                    outcome.update({"public_label": body["public_label"], "model_public_label": body["model_public_label"], "model_score": body["model_score"], "decision_threshold": body["decision_threshold"], "decision_source": body["decision_source"], "evidence_adjusted": body["evidence_adjusted"], "evidence_relationship": body["evidence_relationship"], "retrieval_status": body["retrieval_status"], "related_source_urls": [item["url"] for item in body["related_sources"]], "fact_check_status": body["fact_check_status"]})
                else:
                    outcome["error"] = response.json().get("detail", "Request failed")
            except Exception as exc:
                outcome.update({"http_status": None, "error": type(exc).__name__})
            results.append(outcome)
    reviewed = [item for item in results if item["review_status"] == "adjudicated" and item["human_label"] in ("Misleading", "Non-Misleading") and item["evidence_url_recorded"] and item["http_status"] == 200]
    counts = Counter((item["human_label"], item["public_label"]) for item in reviewed)
    tp = counts[("Misleading", "Potentially Misleading")]
    tn = counts[("Non-Misleading", "No Misleading Information Detected")]
    fp = counts[("Non-Misleading", "Potentially Misleading")]
    fn = counts[("Misleading", "No Misleading Information Detected")]
    n = len(reviewed)
    def ratio(a, b):
        return a / b if b else None
    def f1(precision, recall):
        return 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    misleading_precision, misleading_recall = ratio(tp, tp + fp), ratio(tp, tp + fn)
    clear_precision, clear_recall = ratio(tn, tn + fn), ratio(tn, tn + fp)
    misleading_f1, clear_f1 = f1(misleading_precision, misleading_recall), f1(clear_precision, clear_recall)
    report = {"batch_id": "suriph-human-eval-v1-20261029", "api_origin": BASE, "model": {"run_id": ready["model"]["training_run_id"], "sha256": ready["model"]["sha256"], "threshold": ready["model"]["decision_threshold"]}, "total_cases": len(results), "adjudicated_with_evidence_and_http_200": n, "unresolved_or_failed": len(results) - n, "complete": n == len(results), "counts": {"TN": tn, "FP": fp, "FN": fn, "TP": tp}, "metrics_on_adjudicated_cases_only": {"accuracy": ratio(tp + tn, n), "false_positive_rate": ratio(fp, tn + fp), "false_negative_rate": ratio(fn, tp + fn), "misleading_precision": misleading_precision, "misleading_recall": misleading_recall, "misleading_f1": misleading_f1, "non_misleading_precision": clear_precision, "non_misleading_recall": clear_recall, "non_misleading_f1": clear_f1, "macro_f1": (misleading_f1 + clear_f1) / 2 if misleading_f1 is not None and clear_f1 is not None else None}, "sampling_note": "Balanced inherited-label and word-length strata; metrics are descriptive for this selected batch, not a population estimate.", "cases": results}
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("total_cases", "adjudicated_with_evidence_and_http_200", "unresolved_or_failed", "complete", "counts", "metrics_on_adjudicated_cases_only")}))


if __name__ == "__main__":
    main()
