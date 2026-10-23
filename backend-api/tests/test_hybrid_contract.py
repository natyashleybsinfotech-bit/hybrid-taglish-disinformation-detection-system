"""Contract/failure tests. Test doubles never enter the production runtime."""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.hybrid_pipeline import HybridPipeline, prepare_text
from src.model_runtime import ACTIVE_PROFILE, ModelRuntime, ModelUnavailableError, THRESHOLD
import config


class HybridContractTests(unittest.TestCase):
    def test_whitespace_only_preparation_preserves_case_and_punctuation(self):
        self.assertEqual(prepare_text("  GRABE!!!\n\tHello po?  "), "GRABE!!! Hello po?")
        for text in ("", " \t\r\n "):
            with self.assertRaises(ValueError):
                ModelRuntime().predict(text)

    def test_saved_threshold_is_used_instead_of_argmax(self):
        runtime = ModelRuntime()
        runtime._error = None
        runtime._device = "cpu"
        runtime._pipeline = Mock()
        runtime._pipeline.bundle = {"threshold": THRESHOLD}
        below = THRESHOLD - .01
        runtime._pipeline.infer.return_value = (np.array([below, THRESHOLD]), np.zeros((2, 7)), [1, 1], [2, 2])
        predictions = runtime.predict_many(["one input", "second input"])
        self.assertEqual([p.predicted_class for p in predictions], [0, 1])
        self.assertEqual([p.model_score for p in predictions], [below, THRESHOLD])
        self.assertEqual([p.public_label for p in predictions], ["No Misleading Information Detected", "Potentially Misleading"])
        self.assertEqual([p.to_dict()["displayed_class_score"] for p in predictions], [1 - below, THRESHOLD])
        self.assertEqual([p.to_dict()["misleading_probability"] for p in predictions], [below, THRESHOLD])
        runtime._pipeline.infer.assert_called_once_with(["one input", "second input"])

    def test_failure_clears_readiness_and_never_returns_a_label(self):
        runtime = ModelRuntime()
        runtime._error = None
        runtime._pipeline = Mock()
        runtime._pipeline.infer.side_effect = RuntimeError("encoder failed")
        with self.assertRaisesRegex(ModelUnavailableError, "encoder failed"):
            runtime.predict("new supplied input")
        self.assertFalse(runtime.health()["ready"])
        with self.assertRaises(ModelUnavailableError):
            runtime.predict("another supplied input")

    def test_resources_initialize_once_and_not_during_requests(self):
        runtime = ModelRuntime()
        pipeline = Mock(device="cpu")
        with patch.object(runtime, "_validate_artifacts", return_value={}) as validate, patch(
            "src.model_runtime.HybridPipeline", return_value=pipeline
        ) as constructor:
            runtime.initialize()
            runtime.initialize()
            validate.assert_called_once()
            constructor.assert_called_once()
            pipeline.infer.assert_called_once()

    def test_hash_mismatch_is_rejected_before_unpickling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            encoder = root / "models/contextual_encoder"
            encoder.mkdir(parents=True)
            for name in (Path(path).name for path in ACTIVE_PROFILE["encoder_files"]):
                (encoder / name).write_bytes(b"test fixture")
            classifier = root / ACTIVE_PROFILE["classifier"]
            classifier.parent.mkdir(parents=True, exist_ok=True)
            classifier.write_bytes(b"corrupt artifact")
            (root / "models/tagalog_tokenizer").write_bytes(b"test fixture")
            (root / "models/feature_config.json").write_text("{}")
            (root / ACTIVE_PROFILE["metadata_file"]).write_text("{}")
            if ACTIVE_PROFILE.get("protocol_file"):
                (root / ACTIVE_PROFILE["protocol_file"]).write_text("{}")
            with patch("joblib.load") as load:
                state = ModelRuntime(root).initialize()
                self.assertFalse(state["ready"])
                self.assertIn("SHA-256", state["error"])
                load.assert_not_called()

    def test_missing_encoder_does_not_download_or_load_an_alternative(self):
        with tempfile.TemporaryDirectory() as directory, patch("joblib.load") as load:
            root = Path(directory)
            (root / "models").mkdir()
            (root / "models/model_1.joblib").write_bytes(b"must not load")
            state = ModelRuntime(root).initialize()
            self.assertFalse(state["ready"])
            self.assertIn(Path(ACTIVE_PROFILE["classifier"]).name, state["error"])
            self.assertIn("contextual_encoder", state["error"])
            load.assert_not_called()

    def test_chunk_pooling_weights_all_content_and_excludes_only_added_specials(self):
        import torch
        class Tokenizer:
            cls_token_id, sep_token_id = 10000, 10001
            def __call__(self, text, **kwargs):
                self.assert_no_truncation = kwargs["truncation"] is False
                return {"input_ids": list(map(int, text.split()))}
            def prepare_for_model(self, part, **kwargs):
                raise AssertionError("Training-compatible chunk construction must be manual")
            def pad(self, chunks, **kwargs):
                width = max(len(c["input_ids"]) for c in chunks)
                return {key: torch.tensor([c[key] + [0] * (width - len(c[key])) for c in chunks]) for key in chunks[0]}
        class Encoder:
            def __call__(self, **batch):
                return type("Output", (), {"last_hidden_state": batch["input_ids"].float().unsqueeze(-1).repeat(1, 1, 768)})()
        pipeline = HybridPipeline.__new__(HybridPipeline)
        pipeline.torch, pipeline.tokenizer, pipeline.encoder = torch, Tokenizer(), Encoder()
        pipeline.device, pipeline.batch_size = "cpu", 8
        # Includes a content token with the same value as CLS. It must be retained.
        values = [1] * 510 + [10000, 3]
        vectors, chunks, totals = pipeline.embed_texts([" ".join(map(str, values)), "9"])
        self.assertEqual(chunks, [2, 1])
        self.assertEqual(list(totals), [512, 1])
        self.assertTrue(pipeline.tokenizer.assert_no_truncation)
        np.testing.assert_allclose(vectors[0], np.float32(sum(values) / len(values)))
        np.testing.assert_allclose(vectors[1], 9.0)
        with patch('src.hybrid_pipeline.time.monotonic', side_effect=[0, 121]), self.assertRaises(TimeoutError):
            pipeline.embed_texts(['1'])

    def test_classifier_probability_column_comes_from_classes(self):
        pipeline = HybridPipeline.__new__(HybridPipeline)
        pipeline.embed_texts = Mock(return_value=(np.zeros((1, 768), dtype=np.float32), [1], [3]))
        pipeline.linguistic_features = Mock(return_value=np.zeros(7, dtype=np.float32))
        scaler = Mock()
        scaler.transform.side_effect = lambda matrix: matrix
        estimator = Mock(classes_=np.array([1, 0]))
        estimator.predict_proba.return_value = [[.8, .2]]
        pipeline.bundle = {"context_scaler": scaler, "ling_scaler": scaler, "classifier": estimator}
        self.assertEqual(pipeline.infer(["fresh text"])[0][0], .8)
        estimator.predict_proba.return_value = [[float("nan"), .2]]
        with self.assertRaisesRegex(ValueError, "Invalid classifier probabilities"):
            pipeline.infer(["fresh text"])


if __name__ == "__main__":
    unittest.main()
