"""Verify supplied candidate regression texts through fresh raw-text inference."""

import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from src.model_runtime import runtime


def main():
    fixture = runtime.root / "verification/candidate_regression_cases.json"
    if not fixture.is_file():
        raise SystemExit("The ignored local candidate regression fixture is missing")
    cases = json.loads(fixture.read_text(encoding="utf-8"))
    health = runtime.initialize()
    if not health["ready"]:
        raise SystemExit(health["error"])
    predictions = runtime.predict_many([case["text"] for case in cases])
    results = []
    passed = True
    for case, prediction in zip(cases, predictions):
        delta = abs(prediction.model_score - case["expected_p_misleading"])
        case_passed = delta <= case["atol"] and prediction.predicted_class == case["expected_label"]
        passed &= case_passed
        results.append({
            "name": case["name"],
            "p_misleading": prediction.model_score,
            "expected_p_misleading": case["expected_p_misleading"],
            "absolute_error": delta,
            "tolerance": case["atol"],
            "predicted_class": prediction.predicted_class,
            "decision_threshold": prediction.decision_threshold,
            "chunk_count": prediction.chunk_count,
            "content_token_count": prediction.content_token_count,
            "passed": case_passed,
        })
    report = {
        "model": health,
        "results": results,
        "passed": bool(passed),
        "training_or_tuning_performed": False,
    }
    output = BASE.parent / "docs/CANDIDATE-REGRESSION-VERIFICATION.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
