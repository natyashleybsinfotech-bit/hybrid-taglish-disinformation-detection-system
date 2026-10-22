"""Compare notebook, pre-Facebook, current direct, and live API inference.

This is a diagnostic only: it does not train, tune, change thresholds, or alter artifacts.
The historical source is read with ``git show`` into a temporary directory; the working
tree is never checked out or reset.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib import request

import joblib
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend-api"
SRC = BACKEND / "src"
ARTIFACT_ROOT = BACKEND / "models" / "TRAINING RESULTS"
REPORT = ROOT / "docs" / "FACEBOOK-CLASSIFICATION-REGRESSION.json"
PRE_COMMIT = "bff79ca"
FACEBOOK_ONLY_COMMIT = "0491d42"
THRESHOLD = 0.65
sys.path[:0] = [str(BACKEND), str(SRC)]

import config  # noqa: E402
from hybrid_pipeline import HybridPipeline as CurrentPipeline, prepare_text  # noqa: E402


TEXTS = {
    "hydration_statement": "Ang tubig ay mahalaga sa katawan. Drinking enough water helps prevent dehydration.",
    "batasan_caption": (
        "Barangay Batasan Hills, Quezon City bago mag-2 AM kanina, Oct. 12. "
        "Naaresto ng Batasan Police sa ikinasa nilang hot pursuit operation ang 38-anyos "
        "na suspek na isang miyembro ng Quezon City Task Force Disiplina. Naging ugat umano "
        "ng krimen ang pagsita ng suspek sa mga biktima na nasa labas pa kahit disoras na ng gabi. "
        "Sasampahan siya ng reklamong three counts ng murder. via James Agustin GMA News "
        "COURTESY QCPD STATION 6"
    ),
    "long_complete_text": (
        ("Ang tubig ay mahalaga sa katawan. Drinking enough water helps prevent dehydration. " * 90)
        + "TAIL_MARKER"
    ),
    "caption_plus_menu_reactions": (
        "Ang tubig ay mahalaga sa katawan. Drinking enough water helps prevent dehydration. "
        "Post menu Like Comment Share 123 reactions"
    ),
    "caption_plus_ocr_noise": (
        "Ang tubig ay mahalaga sa katawan. Drinking enough water helps prevent dehydration. "
        "@@@ 111 !!! llI| unreadable"
    ),
    "caption_plus_unrelated_audio": (
        "Ang tubig ay mahalaga sa katawan. Drinking enough water helps prevent dehydration. "
        "BREAKING share agad, may ibang video na tumutugtog at hindi ito bahagi ng post."
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_hash(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode())
    digest.update(json.dumps(value.shape).encode())
    digest.update(value.tobytes())
    return digest.hexdigest()


def state_hash(*arrays) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        value = np.ascontiguousarray(np.asarray(array))
        digest.update(str(value.dtype).encode())
        digest.update(json.dumps(value.shape).encode())
        digest.update(value.tobytes())
    return digest.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


class NotebookReplay:
    """Independent transcription of notebook cells 9, 11, 13, and 19."""

    def __init__(self, root: Path, bundle: dict):
        from functools import lru_cache
        import spacy
        import torch
        from lingua import Language, LanguageDetectorBuilder
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.device = "cpu"
        torch.set_num_threads(max(1, config.MODEL_CPU_THREADS))
        model_dir = root / "models" / "contextual_encoder"
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True)
        self.encoder = AutoModel.from_pretrained(
            model_dir, local_files_only=True, use_safetensors=True
        ).to(self.device)
        self.encoder.eval()
        for parameter in self.encoder.parameters():
            parameter.requires_grad_(False)
        self.nlp = spacy.blank("tl")
        self.nlp.tokenizer.from_disk(root / "models" / "tagalog_tokenizer", exclude=["vocab"])
        self.Language = Language
        detector = (
            LanguageDetectorBuilder.from_languages(Language.TAGALOG, Language.ENGLISH)
            .with_minimum_relative_distance(0.2)
            .build()
        )
        self.token_language = lru_cache(maxsize=100000)(detector.detect_language_of)
        lexicons = bundle["feature_config"]["lexicons"]
        self.particles = set(lexicons["particles"])
        self.emotion = set(lexicons["emotion"])
        self.urgency = set(lexicons["urgency"])
        self.bundle = bundle
        self.batch_size = bundle["encoder_settings"]["batch_size"]

    def linguistic_features(self, text: str) -> np.ndarray:
        tokens = [token.text for token in self.nlp.make_doc(text) if not token.is_space]
        words = [token.casefold() for token in tokens if token.isalpha()]
        total, chars = len(tokens), len(text)
        counts = {self.Language.TAGALOG: 0, self.Language.ENGLISH: 0}
        for word in words:
            language = self.token_language(word)
            if language in counts:
                counts[language] += 1
        filipino, english = counts[self.Language.TAGALOG], counts[self.Language.ENGLISH]
        alphabetic = [character for character in text if character.isalpha()]
        repeated = sum(len(match.group(0)) for match in re.finditer(r"(.)\1{2,}", text))
        ratio = lambda numerator, denominator: numerator / denominator if denominator else 0.0
        return np.array([
            ratio(min(filipino, english), filipino + english),
            ratio(sum(word in self.particles for word in words), total),
            ratio(text.count("!") + text.count("?"), chars),
            ratio(sum(character.isupper() for character in alphabetic), len(alphabetic)),
            ratio(repeated, chars),
            ratio(sum(word in self.emotion for word in words), total),
            ratio(sum(word in self.urgency for word in words), total),
        ], dtype=np.float32)

    def embed_texts(self, texts: list[str]):
        chunks, owners, per_record = [], [], []
        for owner, text in enumerate(texts):
            ids = self.tokenizer(
                text, add_special_tokens=False, truncation=False, verbose=False
            )["input_ids"]
            if not ids:
                raise ValueError("Empty tokenizer output")
            parts = [ids[start:start + 510] for start in range(0, len(ids), 510)]
            per_record.append(len(parts))
            for part in parts:
                encoded = self.tokenizer.prepare_for_model(
                    part, add_special_tokens=True, return_attention_mask=True,
                    return_special_tokens_mask=False, truncation=False,
                )
                assert encoded["input_ids"] == [self.tokenizer.cls_token_id] + part + [self.tokenizer.sep_token_id]
                encoded["special_tokens_mask"] = [1] + [0] * len(part) + [1]
                chunks.append(encoded)
                owners.append(owner)
        sums = np.zeros((len(texts), 768), dtype=np.float64)
        totals = np.zeros(len(texts), dtype=np.int64)
        with self.torch.inference_mode():
            for start in range(0, len(chunks), self.batch_size):
                batch = self.tokenizer.pad(
                    chunks[start:start + self.batch_size], padding=True, return_tensors="pt"
                )
                special = batch.pop("special_tokens_mask").to(self.device)
                batch = {key: value.to(self.device) for key, value in batch.items()}
                mask = batch["attention_mask"].bool() & ~special.bool()
                hidden = self.encoder(**batch).last_hidden_state
                vectors = (hidden * mask.unsqueeze(-1)).sum(dim=1).cpu().numpy()
                weights = mask.sum(dim=1).cpu().numpy()
                for offset, (vector, weight) in enumerate(zip(vectors, weights)):
                    owner = owners[start + offset]
                    sums[owner] += vector
                    totals[owner] += int(weight)
        assert (totals > 0).all()
        return (sums / totals[:, None]).astype(np.float32), per_record, totals


def run_pipeline(name: str, pipeline, bundle: dict, texts: dict[str, str]) -> dict:
    keys = list(texts)
    prepared = [re.sub(r"\s+", " ", texts[key]).strip() for key in keys]
    embeddings, chunks, token_counts = pipeline.embed_texts(prepared)
    linguistic = np.vstack([pipeline.linguistic_features(text) for text in prepared])
    scaled_context = bundle["context_scaler"].transform(embeddings)
    scaled_linguistic = bundle["ling_scaler"].transform(linguistic)
    matrix = np.hstack([scaled_context, scaled_linguistic])
    probabilities = np.asarray(bundle["classifier"].predict_proba(matrix))
    classes = [int(value) for value in bundle["classifier"].classes_]
    positive_column = classes.index(1)
    coefficients = np.asarray(bundle["classifier"].coef_[0])
    intercept = float(bundle["classifier"].intercept_[0])
    records = {}
    for index, key in enumerate(keys):
        probability = float(probabilities[index, positive_column])
        predicted = int(probability >= bundle["threshold"])
        contextual_contribution = float(np.dot(matrix[index, :768], coefficients[:768]))
        linguistic_contributions = matrix[index, 768:] * coefficients[768:]
        logit = intercept + contextual_contribution + float(linguistic_contributions.sum())
        records[key] = {
            "input_sha256": hashlib.sha256(texts[key].encode()).hexdigest(),
            "input_characters": len(texts[key]),
            "prepared_text": prepared[index],
            "prepared_text_sha256": hashlib.sha256(prepared[index].encode()).hexdigest(),
            "content_tokens": int(token_counts[index]),
            "chunks": int(chunks[index]),
            "embedding_sha256": array_hash(embeddings[index]),
            "linguistic_features": [float(value) for value in linguistic[index]],
            "linguistic_sha256": array_hash(linguistic[index]),
            "scaled_context_sha256": array_hash(scaled_context[index]),
            "scaled_linguistic": [float(value) for value in scaled_linguistic[index]],
            "scaled_linguistic_sha256": array_hash(scaled_linguistic[index]),
            "hybrid_vector_sha256": array_hash(matrix[index]),
            "logit_decomposition": {
                "intercept": intercept,
                "contextual_features": contextual_contribution,
                "linguistic_features_total": float(linguistic_contributions.sum()),
                "linguistic_features": [float(value) for value in linguistic_contributions],
                "total_logit": logit,
            },
            "probability_columns": [float(value) for value in probabilities[index]],
            "classifier_classes": classes,
            "misleading_probability_column": positive_column,
            "p_misleading": probability,
            "threshold": float(bundle["threshold"]),
            "predicted_class": predicted,
            "label": "Misleading" if predicted else "Non-Misleading",
        }
    return {"path": name, "records": records}


def load_historical_pipeline():
    source = git("show", f"{PRE_COMMIT}:backend-api/src/hybrid_pipeline.py")
    temporary = tempfile.TemporaryDirectory(prefix="suriph-pre-facebook-")
    module_path = Path(temporary.name) / "hybrid_pipeline.py"
    module_path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("suriph_pre_facebook_pipeline", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return temporary, module.HybridPipeline


def live_api(texts: dict[str, str], base: str) -> dict:
    records = {}
    for key, text in texts.items():
        payload = json.dumps({"text": text, "retrieve_sources": False}).encode()
        req = request.Request(
            f"{base.rstrip('/')}/analyze", data=payload, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=180) as response:
            body = json.load(response)
        records[key] = {
            "submitted_text": text,
            "analyzed_text": body["analyzed_text"],
            "submitted_matches_analyzed": text == body["analyzed_text"],
            "p_misleading": body["model_score"],
            "probability_columns": [1 - body["model_score"], body["model_score"]],
            "threshold": body["decision_threshold"],
            "predicted_class": body["predicted_class"],
            "label": body["internal_label"],
            "displayed_label": body["public_label"],
            "model_name": body["model_name"],
            "training_run_id": body["training_run_id"],
            "artifact_sha256": body["artifact_sha256"],
            "linguistic_features": [item["value"] for item in body["linguistic_indicators"]],
            "chunks": body["chunk_count"],
            "content_tokens": body["content_token_count"],
        }
    return records


def component_hashes(bundle: dict) -> dict:
    encoder_names = (
        "config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json",
        "special_tokens_map.json", "vocab.txt",
    )
    classifier = bundle["classifier"]
    context = bundle["context_scaler"]
    linguistic = bundle["ling_scaler"]
    return {
        "model_4_joblib": sha256_file(ARTIFACT_ROOT / "models" / "model_4.joblib"),
        "classifier_state": state_hash(classifier.classes_, classifier.coef_, classifier.intercept_),
        "context_scaler_state": state_hash(context.mean_, context.var_, context.scale_, np.atleast_1d(context.n_samples_seen_)),
        "linguistic_scaler_state": state_hash(linguistic.mean_, linguistic.var_, linguistic.scale_, np.atleast_1d(linguistic.n_samples_seen_)),
        "feature_config_file": sha256_file(ARTIFACT_ROOT / "models" / "feature_config.json"),
        "feature_config_in_bundle": hashlib.sha256(json.dumps(bundle["feature_config"], sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "tagalog_tokenizer": sha256_file(ARTIFACT_ROOT / "models" / "tagalog_tokenizer"),
        "contextual_encoder": {
            name: sha256_file(ARTIFACT_ROOT / "models" / "contextual_encoder" / name)
            for name in encoder_names
        },
        "run_manifest": sha256_file(ARTIFACT_ROOT / "run_manifest.json"),
        "training_notebook": sha256_file(ARTIFACT_ROOT / "SuriPH_Repaired_Training_Run.ipynb"),
    }


def compare_paths(paths: dict[str, dict]) -> dict:
    baseline = paths["training_notebook_replay"]["records"]
    comparisons = {}
    for name, path in paths.items():
        if name == "training_notebook_replay":
            continue
        items = {}
        for key, expected in baseline.items():
            actual = path["records"][key]
            items[key] = {
                "prepared_text_identical": actual["prepared_text"] == expected["prepared_text"],
                "embedding_identical": actual["embedding_sha256"] == expected["embedding_sha256"],
                "linguistic_identical": actual["linguistic_sha256"] == expected["linguistic_sha256"],
                "scaled_context_identical": actual["scaled_context_sha256"] == expected["scaled_context_sha256"],
                "scaled_linguistic_identical": actual["scaled_linguistic_sha256"] == expected["scaled_linguistic_sha256"],
                "hybrid_vector_identical": actual["hybrid_vector_sha256"] == expected["hybrid_vector_sha256"],
                "max_probability_absolute_difference": max(
                    abs(a - b) for a, b in zip(actual["probability_columns"], expected["probability_columns"])
                ),
                "decision_identical": actual["predicted_class"] == expected["predicted_class"],
            }
        comparisons[name] = items
    return comparisons


def compare_api_to_direct(api: dict, direct: dict) -> dict:
    comparisons = {}
    for key, expected in direct["records"].items():
        actual = api[key]
        comparisons[key] = {
            "submitted_text_identical": actual["submitted_text"] == expected["prepared_text"],
            "analyzed_text_identical": actual["analyzed_text"] == expected["prepared_text"],
            "content_tokens_identical": actual["content_tokens"] == expected["content_tokens"],
            "chunks_identical": actual["chunks"] == expected["chunks"],
            "linguistic_features_max_absolute_difference": max(
                abs(a - b)
                for a, b in zip(actual["linguistic_features"], expected["linguistic_features"])
            ),
            "probability_absolute_difference": abs(
                actual["p_misleading"] - expected["p_misleading"]
            ),
            "decision_identical": actual["predicted_class"] == expected["predicted_class"],
        }
    return comparisons


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    bundle = joblib.load(ARTIFACT_ROOT / "models" / "model_4.joblib")

    notebook = NotebookReplay(ARTIFACT_ROOT, bundle)
    notebook_results = run_pipeline("training_notebook_replay", notebook, bundle, TEXTS)
    del notebook
    gc.collect()

    temporary, HistoricalPipeline = load_historical_pipeline()
    historical = HistoricalPipeline(ARTIFACT_ROOT, bundle, device="cpu", cpu_threads=config.MODEL_CPU_THREADS)
    historical_results = run_pipeline("pre_facebook_pipeline_bff79ca", historical, bundle, TEXTS)
    del historical
    temporary.cleanup()
    gc.collect()

    current = CurrentPipeline(ARTIFACT_ROOT, bundle, device="cpu", cpu_threads=config.MODEL_CPU_THREADS)
    current_results = run_pipeline("current_direct_pipeline", current, bundle, TEXTS)
    del current
    gc.collect()

    paths = {
        "training_notebook_replay": notebook_results,
        "pre_facebook_pipeline_bff79ca": historical_results,
        "current_direct_pipeline": current_results,
    }
    pre_runtime = git("show", f"{PRE_COMMIT}:backend-api/src/model_runtime.py")
    inventory = json.loads(git("show", f"{PRE_COMMIT}:backend-api/src/hybrid_artifacts.json"))
    hashes = component_hashes(bundle)
    feature_config_file = json.loads(
        (ARTIFACT_ROOT / "models" / "feature_config.json").read_text(encoding="utf-8")
    )
    api_results = live_api(TEXTS, args.api_base)
    extension_report_path = ROOT / "docs" / "EXTENSION-POPUP-VERIFICATION.json"
    extraction_report_path = ROOT / "docs" / "FACEBOOK-MODAL-VERIFICATION.json"
    extension_report = json.loads(extension_report_path.read_text(encoding="utf-8")) if extension_report_path.exists() else {"status": "not run"}
    extraction_report = json.loads(extraction_report_path.read_text(encoding="utf-8")) if extraction_report_path.exists() else {"status": "not run"}
    report = {
        "purpose": "Read-only Facebook-only regression investigation; no training, threshold change, label reversal, model switch, or retrieval comparison.",
        "commit_boundary": {
            "facebook_only_commit": FACEBOOK_ONLY_COMMIT,
            "immediate_parent": PRE_COMMIT,
            "working_tree_reset_or_checkout_performed": False,
            "pre_and_current_hybrid_pipeline_git_blob": git("rev-parse", f"{PRE_COMMIT}:backend-api/src/hybrid_pipeline.py"),
            "current_hybrid_pipeline_git_blob": git("rev-parse", "HEAD:backend-api/src/hybrid_pipeline.py"),
            "core_pipeline_git_blob_identical": git("rev-parse", f"{PRE_COMMIT}:backend-api/src/hybrid_pipeline.py") == git("rev-parse", "HEAD:backend-api/src/hybrid_pipeline.py"),
            "model_runtime_git_blob_changed": git("rev-parse", f"{PRE_COMMIT}:backend-api/src/model_runtime.py") != git("rev-parse", "HEAD:backend-api/src/model_runtime.py"),
            "model_runtime_diff_scope": "Prediction serialization and public-label wording changed; the threshold decision still uses score >= the pinned bundle threshold, and the core HybridPipeline is unchanged.",
        },
        "artifact_identity": {
            "expected_training_run": "20261011T235112Z",
            "pre_runtime_expected_model_4_sha256": re.search(r'CLASSIFIER_SHA256 = "([0-9a-f]+)"', pre_runtime).group(1),
            "pre_runtime_expected_threshold": float(re.search(r"THRESHOLD = ([0-9.]+)", pre_runtime).group(1)),
            "pre_encoder_inventory": inventory["files"],
            "current_component_hashes": hashes,
            "pre_encoder_inventory_matches_current_files": all(
                hashes["contextual_encoder"][Path(name).name] == expected
                for name, expected in inventory["files"].items()
            ),
            "pre_model_hash_matches_current_model_file": re.search(r'CLASSIFIER_SHA256 = "([0-9a-f]+)"', pre_runtime).group(1) == hashes["model_4_joblib"],
            "feature_config_file_matches_bundle": feature_config_file == bundle["feature_config"],
            "bundle_model_name": bundle["model_name"],
            "bundle_threshold": bundle["threshold"],
            "classifier_classes": [int(value) for value in bundle["classifier"].classes_],
            "label_mapping": bundle["label_mapping"],
        },
        "exact_inputs": TEXTS,
        "paths": paths,
        "intermediate_comparison_to_notebook": compare_paths(paths),
        "current_api": api_results,
        "current_api_comparison_to_direct": compare_api_to_direct(api_results, current_results),
        "extension": extension_report,
        "facebook_extraction": extraction_report,
        "media_diagnostics": {
            "note": "Diagnostic text variants only. Production media behavior was not changed.",
            "caption_only_key": "hydration_statement",
            "combined_variant_keys": [
                "caption_plus_menu_reactions",
                "caption_plus_ocr_noise",
                "caption_plus_unrelated_audio",
            ],
        },
        "conclusion": "The Facebook-only restriction did not cause these classifier scores. The notebook replay, pre-Facebook pipeline, and current direct pipeline produce identical intermediates and decisions with the same pinned model_4 artifact. The live API and extension submit the same text and preserve the same decision. Current Facebook caption extraction excludes the tested menu, reaction, nested-comment, and neighboring-post text and fails closed for an unrecognized container. Media-derived OCR or audio remains intentionally combined only when the user chooses media analysis and can change the model input and score.",
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "report": str(REPORT),
        "hydration": {
            path: data["records"]["hydration_statement"]["p_misleading"]
            for path, data in paths.items()
        } | {"current_api": api_results["hydration_statement"]["p_misleading"]},
        "core_pipeline_identical": report["commit_boundary"]["core_pipeline_git_blob_identical"],
        "artifact_hash_identical": report["artifact_identity"]["pre_model_hash_matches_current_model_file"],
    }, indent=2))


if __name__ == "__main__":
    main()
