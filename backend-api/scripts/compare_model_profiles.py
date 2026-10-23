"""Offline, read-only component fingerprint comparison for candidate and rollback."""

import hashlib
import json
from pathlib import Path
import sys
import warnings

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

import joblib
import numpy as np
from sklearn.exceptions import InconsistentVersionWarning
from src.model_runtime import PROFILES, sha256


def array_fingerprint(*arrays) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        value = np.ascontiguousarray(array)
        digest.update(str(value.dtype).encode())
        digest.update(json.dumps(value.shape).encode())
        digest.update(value.tobytes())
    return digest.hexdigest()


def inspect(profile_id: str):
    profile = PROFILES[profile_id]
    root = (BASE / profile["artifact_directory"]).resolve()
    path = root / profile["classifier"]
    actual_hash = sha256(path)
    if actual_hash != profile["classifier_sha256"]:
        raise RuntimeError(f"Refusing unverified bundle for {profile_id}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InconsistentVersionWarning)
        bundle = joblib.load(path)
    classifier = bundle["classifier"]
    return {
        "run_id": profile_id,
        "classifier_file": path.name,
        "classifier_bundle_sha256": actual_hash,
        "encoder_files_sha256": profile["encoder_files"],
        "feature_config_sha256": sha256(root / "models/feature_config.json"),
        "tagalog_tokenizer_sha256": sha256(root / "models/tagalog_tokenizer"),
        "context_scaler_state_sha256": array_fingerprint(
            bundle["context_scaler"].mean_, bundle["context_scaler"].scale_, bundle["context_scaler"].var_
        ),
        "linguistic_scaler_state_sha256": array_fingerprint(
            bundle["ling_scaler"].mean_, bundle["ling_scaler"].scale_, bundle["ling_scaler"].var_
        ),
        "classifier_state_sha256": array_fingerprint(
            classifier.classes_, classifier.coef_, classifier.intercept_
        ),
        "threshold": float(bundle["threshold"]),
        "classes": [int(value) for value in classifier.classes_],
        "feature_count": int(classifier.n_features_in_),
    }


def main():
    stable = inspect("20261011T235112Z")
    candidate = inspect("full-cleaned-20261023T022416Z")
    report = {
        "purpose": "Offline component identity comparison; neither profile was served or selected by this script.",
        "stable_rollback": stable,
        "local_candidate": candidate,
        "same_feature_config": stable["feature_config_sha256"] == candidate["feature_config_sha256"],
        "same_tagalog_tokenizer": stable["tagalog_tokenizer_sha256"] == candidate["tagalog_tokenizer_sha256"],
        "same_context_scaler_state": stable["context_scaler_state_sha256"] == candidate["context_scaler_state_sha256"],
        "same_linguistic_scaler_state": stable["linguistic_scaler_state_sha256"] == candidate["linguistic_scaler_state_sha256"],
        "same_classifier_state": stable["classifier_state_sha256"] == candidate["classifier_state_sha256"],
        "training_or_tuning_performed": False,
    }
    output = BASE.parent / "docs/CANDIDATE-COMPONENT-COMPARISON.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
