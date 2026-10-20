"""One pinned SuriPH hybrid classifier; explicit startup, fail-closed inference."""

from dataclasses import asdict, dataclass, field
import hashlib
import importlib.metadata
import json
from pathlib import Path
import threading

import config
try:
    from .hybrid_pipeline import FEATURE_NAMES, HybridPipeline, prepare_text
except ImportError:
    from hybrid_pipeline import FEATURE_NAMES, HybridPipeline, prepare_text

RUN_ID = "20261011T235112Z"
CLASSIFIER_SHA256 = "72d87971ee2af7fca1f6f0a9b94bbe92618bd92ce8c5e48e35b80882e1321c7c"
MODEL_NAME = "Hybrid DistilBERT + linguistic + LR"
THRESHOLD = 0.65
# Historical training-module imports only. Schema-1 bundles are not loadable.
BUNDLE_SCHEMA_VERSION = 1


class ModelUnavailableError(RuntimeError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


normalize_text = prepare_text


@dataclass(frozen=True)
class Prediction:
    internal_label: str
    public_label: str
    confidence: float  # Deprecated compatibility field: score of the selected class.
    model_status: str
    model_name: str
    model_version: str
    model_score: float = 0.0  # Always P(class 1 / Misleading), not calibrated certainty.
    predicted_class: int = 0
    decision_threshold: float = THRESHOLD
    training_run_id: str = RUN_ID
    artifact_sha256: str = CLASSIFIER_SHA256
    device: str = "unknown"
    chunk_count: int = 0
    content_token_count: int = 0
    linguistic_indicators: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self) | {"score_class": "Misleading", "score_description": "Model score for the Misleading class; not calibrated certainty or a verified factual verdict."}


class ModelRuntime:
    def __init__(self, root=None):
        self.root = Path(root or config.MODEL_ARTIFACT_DIR).resolve()
        self.path = self.root / "models" / "model_4.joblib"
        self._lock = threading.RLock()
        self._pipeline = None
        self._attempted = False
        self._error = "Model has not been initialized at backend startup."
        self._hash = None
        self._device = None
        self._versions = {}

    def _validate_artifacts(self):
        import joblib
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        required = ["run_manifest.json", "models/model_4.joblib", "models/feature_config.json", "models/tagalog_tokenizer"]
        required += [f"models/contextual_encoder/{name}" for name in (
            "config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"
        )]
        missing = [name for name in required if not (self.root / name).is_file()]
        if missing:
            raise ValueError("Missing required artifacts: " + ", ".join(missing))
        manifest = json.loads((self.root / "run_manifest.json").read_text(encoding="utf-8"))
        self._hash = sha256(self.path)
        entry = [item for item in manifest["model_artifacts"] if item["filename"] == "model_4.joblib"]
        if manifest["run_id"] != RUN_ID or len(entry) != 1 or entry[0]["sha256"] != CLASSIFIER_SHA256 or self._hash != CLASSIFIER_SHA256:
            raise ValueError("model_4 SHA-256 or training-run identity mismatch")
        inventory = json.loads(Path(__file__).with_name("hybrid_artifacts.json").read_text(encoding="utf-8"))
        for name, expected_hash in inventory["files"].items():
            if sha256(self.root / name) != expected_hash:
                raise ValueError(f"Saved encoder component SHA-256 mismatch: {name}")
        for name in ("torch", "transformers", "huggingface-hub", "scikit-learn", "numpy", "scipy", "spacy", "lingua-language-detector", "joblib"):
            actual = importlib.metadata.version(name)
            expected = manifest["environment"][name]
            self._versions[name] = actual
            if actual.split("+")[0] != expected.split("+")[0]:
                raise ValueError(f"Incompatible {name} {actual}; expected {expected}. Install requirements-model.txt")
        # Never unpickle an unverified classifier or any alternative artifact.
        bundle = joblib.load(self.path)
        required_keys = {"classifier", "threshold", "selection", "model_name", "label_mapping", "encoder_settings", "feature_config", "context_scaler", "ling_scaler", "checkpoint", "revision"}
        if not isinstance(bundle, dict) or not required_keys <= bundle.keys():
            raise ValueError("model_4 bundle structure is incompatible")
        if bundle["threshold"] != THRESHOLD or bundle["selection"]["threshold"] != THRESHOLD or bundle["model_name"] != MODEL_NAME:
            raise ValueError("Saved hybrid selection/threshold mismatch")
        labels = {"Non-Misleading": 0, "Misleading": 1}
        if bundle["label_mapping"] != labels or manifest["label_mapping"] != labels:
            raise ValueError("Label mapping mismatch")
        if type(bundle["classifier"]) is not LogisticRegression or bundle["classifier"].n_features_in_ != 775 or set(bundle["classifier"].classes_) != {0, 1}:
            raise ValueError("Expected the saved binary 775-feature LogisticRegression")
        for key, width in (("context_scaler", 768), ("ling_scaler", 7)):
            scaler = bundle[key]
            if type(scaler) is not StandardScaler or scaler.n_features_in_ != width or not np.isfinite(scaler.scale_).all():
                raise ValueError(f"Incompatible saved {key}")
        settings = bundle["encoder_settings"]
        expected_settings = dict(mode="frozen", pooling="content-token weighted mean across all non-overlapping chunks", max_length=512, content_tokens_per_chunk=510, embedding_dimensions=768, batch_size=8)
        if settings != manifest["checkpoint_settings"] or any(settings.get(k) != v for k, v in expected_settings.items()):
            raise ValueError("Encoder settings differ from the recorded training behavior")
        if bundle["checkpoint"] != settings["checkpoint"] or bundle["revision"] != settings["resolved_revision"]:
            raise ValueError("Encoder checkpoint/revision mismatch")
        feature_config = json.loads((self.root / "models" / "feature_config.json").read_text(encoding="utf-8"))
        if feature_config != bundle["feature_config"] or list(feature_config["definitions"]) != list(FEATURE_NAMES) or manifest["features"] != list(FEATURE_NAMES):
            raise ValueError("Saved feature configuration/order mismatch")
        if feature_config["token_language_id"] != "Lingua ENGLISH/TAGALOG; minimum_relative_distance=0.2" or feature_config["prepared_text"] != "whitespace collapse only; original text retained":
            raise ValueError("Unsupported language-detector/text preparation settings")
        if sha256(self.root / "models" / "tagalog_tokenizer") != feature_config["calamancy_tokenizer_sha256"]:
            raise ValueError("Saved Tagalog tokenizer SHA-256 mismatch")
        return bundle

    def initialize(self):
        with self._lock:
            if self._attempted:
                return self.health()
            self._attempted = True
            try:
                bundle = self._validate_artifacts()
                pipeline = HybridPipeline(self.root, bundle, device=config.MODEL_DEVICE, cpu_threads=config.MODEL_CPU_THREADS)
                self._device = pipeline.device
                pipeline.infer(["SuriPH startup check: pagsusuri ng balita."])
                self._pipeline = pipeline
                self._error = None
            except Exception as exc:
                self._pipeline = None
                self._error = f"SuriPH hybrid model unavailable: {type(exc).__name__}: {exc}"
            return self.health()

    def health(self):
        ready = self._pipeline is not None and self._error is None
        return {
            "status": "ready" if ready else "unavailable", "ready": ready,
            "name": MODEL_NAME, "classifier": "model_4.joblib", "version": RUN_ID,
            "training_run_id": RUN_ID, "sha256": self._hash, "expected_sha256": CLASSIFIER_SHA256,
            "device": self._device, "feature_mode": "hybrid_distilbert",
            "decision_threshold": THRESHOLD, "label_mapping": {"Non-Misleading": 0, "Misleading": 1},
            "runtime_versions": self._versions, "error": self._error,
            "model_switching_enabled": False, "training_enabled": False,
        }

    def predict_many(self, texts):
        prepared = [prepare_text(text) for text in texts]
        if not prepared or any(not text for text in prepared):
            raise ValueError("Non-empty text is required for screening.")
        if any(len(text) > config.MAX_TEXT_CHARACTERS for text in prepared):
            raise ValueError(f"Text exceeds the explicit {config.MAX_TEXT_CHARACTERS}-character limit; nothing was truncated.")
        with self._lock:
            if self._pipeline is None or self._error:
                raise ModelUnavailableError(self._error or "SuriPH hybrid model is unavailable.")
            try:
                scores, features, chunks, tokens = self._pipeline.infer(prepared)
                threshold = self._pipeline.bundle["threshold"]
                results = []
                for score, values, chunk_count, token_count in zip(scores, features, chunks, tokens):
                    label = int(score >= threshold)
                    name = "Misleading" if label else "Non-Misleading"
                    results.append(Prediction(
                        internal_label=name, public_label=f"Prediction: {name}",
                        confidence=float(score if label else 1 - score), model_status="ready",
                        model_name=MODEL_NAME, model_version=RUN_ID, model_score=float(score),
                        predicted_class=label, decision_threshold=threshold, device=self._device,
                        chunk_count=int(chunk_count), content_token_count=int(token_count),
                        linguistic_indicators=[{"name": name, "value": float(value)} for name, value in zip(FEATURE_NAMES, values)],
                    ))
                return results
            except Exception as exc:
                self._error = f"SuriPH hybrid inference failed: {type(exc).__name__}: {exc}. Restart after resolving the failure."
                self._pipeline = None
                raise ModelUnavailableError(self._error) from exc

    def predict(self, text):
        return self.predict_many([text])[0]


runtime = ModelRuntime()


def classify(text):
    return runtime.predict(text)


def model_health():
    return runtime.health()


def initialize_model():
    return runtime.initialize()


def configure_model(_path):
    raise ModelUnavailableError("Model switching is disabled; only the pinned model_4.joblib is permitted.")
