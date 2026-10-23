"""One explicitly selected SuriPH hybrid classifier; fail-closed inference."""

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


MODEL_NAME = "Hybrid DistilBERT + linguistic + LR"
LABEL_MAPPING = {"Non-Misleading": 0, "Misleading": 1}
PROFILE_PATH = Path(__file__).with_name("model_profiles.json")
PROFILE_DOCUMENT = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
PROFILES = PROFILE_DOCUMENT["profiles"]
APPROVED_PROFILE_CLASSIFIERS = {
    "20261011T235112Z": "models/model_4.joblib",
    "full-cleaned-20261023T022416Z": "models/model_4_full_dataset_CANDIDATE.joblib",
}
if (
    set(PROFILES) != set(APPROVED_PROFILE_CLASSIFIERS)
    or any(PROFILES[name].get("classifier") != path for name, path in APPROVED_PROFILE_CLASSIFIERS.items())
):
    raise RuntimeError("Model profile registry contains an unapproved classifier")
ACTIVE_PROFILE_ID = config.MODEL_PROFILE
if ACTIVE_PROFILE_ID not in PROFILES:
    raise RuntimeError(f"Unknown SURI_MODEL_PROFILE: {ACTIVE_PROFILE_ID}")
ACTIVE_PROFILE = PROFILES[ACTIVE_PROFILE_ID]
RUN_ID = ACTIVE_PROFILE_ID
CLASSIFIER_SHA256 = ACTIVE_PROFILE["classifier_sha256"]
THRESHOLD = float(ACTIVE_PROFILE["expected_threshold"])
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


def _runtime_version(name: str) -> str:
    return importlib.metadata.version(name)


def _version_core(value: str) -> str:
    return value.split("+", 1)[0]


@dataclass(frozen=True)
class Prediction:
    internal_label: str
    public_label: str
    confidence: float
    model_status: str
    model_name: str
    model_version: str
    model_score: float = 0.0
    predicted_class: int = 0
    decision_threshold: float = THRESHOLD
    training_run_id: str = RUN_ID
    artifact_sha256: str = CLASSIFIER_SHA256
    device: str = "unknown"
    chunk_count: int = 0
    content_token_count: int = 0
    linguistic_indicators: list = field(default_factory=list)

    def to_dict(self):
        displayed_score = self.model_score if self.predicted_class == 1 else 1 - self.model_score
        return asdict(self) | {
            "score_class": "Misleading",
            "misleading_probability": self.model_score,
            "displayed_class_score": displayed_score,
            "displayed_score_class": self.internal_label,
            "score_description": "Model score for the selected prediction; not calibrated certainty or a verified factual verdict.",
        }


class ModelRuntime:
    def __init__(self, root=None, profile_id=None):
        self.profile_id = profile_id or ACTIVE_PROFILE_ID
        if self.profile_id not in PROFILES:
            raise ValueError(f"Unknown SuriPH model profile: {self.profile_id}")
        self.profile = PROFILES[self.profile_id]
        configured_root = config.MODEL_ARTIFACT_DIR
        default_root = config.BASE_DIR / self.profile["artifact_directory"]
        self.root = Path(root or configured_root or default_root).resolve()
        self.path = self.root / self.profile["classifier"]
        self._lock = threading.RLock()
        self._pipeline = None
        self._attempted = False
        self._error = "Model has not been initialized at backend startup."
        self._hash = None
        self._device = None
        self._versions = {}
        self._threshold = float(self.profile["expected_threshold"])
        self._model_name = MODEL_NAME

    def _read_metadata(self):
        metadata_path = self.root / self.profile["metadata_file"]
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        kind = self.profile["metadata_kind"]
        if kind == "legacy_manifest":
            entries = [
                item for item in metadata.get("model_artifacts", [])
                if item.get("filename") == Path(self.profile["classifier"]).name
            ]
            if metadata.get("run_id") != self.profile_id or len(entries) != 1:
                raise ValueError("Classifier training-run identity mismatch")
            if entries[0].get("sha256") != self.profile["classifier_sha256"]:
                raise ValueError("Classifier manifest SHA-256 mismatch")
            return metadata, metadata["checkpoint_settings"], metadata["features"], metadata["environment"]
        if kind == "candidate_results":
            protocol = json.loads((self.root / self.profile["protocol_file"]).read_text(encoding="utf-8"))
            if metadata.get("run_id") != self.profile_id:
                raise ValueError("Candidate training-run identity mismatch")
            if metadata.get("model_sha256") != self.profile["classifier_sha256"]:
                raise ValueError("Candidate results SHA-256 mismatch")
            if float(metadata.get("selection", {}).get("threshold")) != self._threshold:
                raise ValueError("Candidate results threshold mismatch")
            return protocol, protocol["encoder_settings"], protocol["linguistic_features"], metadata["environment"]
        raise ValueError(f"Unsupported model metadata kind: {kind}")

    def _validate_artifacts(self):
        import joblib
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        required = [
            self.profile["metadata_file"], self.profile["classifier"],
            "models/feature_config.json", "models/tagalog_tokenizer",
            *self.profile["encoder_files"].keys(),
        ]
        if self.profile.get("protocol_file"):
            required.append(self.profile["protocol_file"])
        missing = [name for name in required if not (self.root / name).is_file()]
        if missing:
            raise ValueError("Missing required artifacts: " + ", ".join(missing))

        self._hash = sha256(self.path)
        if self._hash != self.profile["classifier_sha256"]:
            raise ValueError("Classifier SHA-256 mismatch")
        for name, expected_hash in self.profile["encoder_files"].items():
            if sha256(self.root / name) != expected_hash:
                raise ValueError(f"Saved encoder component SHA-256 mismatch: {name}")

        metadata, metadata_settings, metadata_features, environment = self._read_metadata()
        checked_packages = (
            "torch", "transformers", "huggingface-hub", "scikit-learn", "numpy",
            "scipy", "spacy", "lingua-language-detector", "joblib",
        )
        for name in checked_packages:
            if name not in environment:
                continue
            actual = _runtime_version(name)
            expected = environment[name]
            self._versions[name] = actual
            if _version_core(actual) != _version_core(expected):
                raise ValueError(
                    f"Incompatible {name} {actual}; expected {expected}. "
                    "Use the requirements file for the selected model profile."
                )

        # Never unpickle an unverified classifier or any alternative artifact.
        bundle = joblib.load(self.path)
        required_keys = {
            "classifier", "threshold", "selection", "model_name", "label_mapping",
            "encoder_settings", "feature_config", "context_scaler", "ling_scaler",
            "checkpoint", "revision",
        }
        if not isinstance(bundle, dict) or not required_keys <= bundle.keys():
            raise ValueError("Selected model_4 bundle structure is incompatible")
        if self.profile["metadata_kind"] == "candidate_results":
            if bundle.get("run_id") != self.profile_id or bundle.get("deployment_approved") is not False:
                raise ValueError("Candidate bundle identity or local-trial status mismatch")
        if (
            float(bundle["threshold"]) != self._threshold
            or float(bundle["selection"]["threshold"]) != self._threshold
            or bundle["model_name"] != MODEL_NAME
        ):
            raise ValueError("Saved hybrid selection/threshold mismatch")
        if bundle["label_mapping"] != LABEL_MAPPING:
            raise ValueError("Label mapping mismatch")
        if self.profile["metadata_kind"] == "legacy_manifest" and metadata["label_mapping"] != LABEL_MAPPING:
            raise ValueError("Manifest label mapping mismatch")
        classifier = bundle["classifier"]
        if type(classifier) is not LogisticRegression or classifier.n_features_in_ != 775 or set(classifier.classes_) != {0, 1}:
            raise ValueError("Expected the saved binary 775-feature LogisticRegression")
        for key, width in (("context_scaler", 768), ("ling_scaler", 7)):
            scaler = bundle[key]
            if type(scaler) is not StandardScaler or scaler.n_features_in_ != width or not np.isfinite(scaler.scale_).all():
                raise ValueError(f"Incompatible saved {key}")

        settings = bundle["encoder_settings"]
        expected_settings = {
            "mode": "frozen",
            "pooling": "content-token weighted mean across all non-overlapping chunks",
            "max_length": 512,
            "content_tokens_per_chunk": 510,
            "embedding_dimensions": 768,
            "batch_size": 8,
        }
        if settings != metadata_settings or any(settings.get(key) != value for key, value in expected_settings.items()):
            raise ValueError("Encoder settings differ from the recorded training behavior")
        if bundle["checkpoint"] != settings["checkpoint"] or bundle["revision"] != settings["resolved_revision"]:
            raise ValueError("Encoder checkpoint/revision mismatch")

        feature_path = self.root / "models" / "feature_config.json"
        feature_config = json.loads(feature_path.read_text(encoding="utf-8"))
        if (
            feature_config != bundle["feature_config"]
            or list(feature_config["definitions"]) != list(FEATURE_NAMES)
            or list(metadata_features) != list(FEATURE_NAMES)
        ):
            raise ValueError("Saved feature configuration/order mismatch")
        if feature_config["token_language_id"] != "Lingua ENGLISH/TAGALOG; minimum_relative_distance=0.2" or feature_config["prepared_text"] != "whitespace collapse only; original text retained":
            raise ValueError("Unsupported language-detector/text preparation settings")
        if sha256(self.root / "models" / "tagalog_tokenizer") != feature_config["calamancy_tokenizer_sha256"]:
            raise ValueError("Saved Tagalog tokenizer SHA-256 mismatch")
        self._threshold = float(bundle["threshold"])
        self._model_name = bundle["model_name"]
        return bundle

    def initialize(self):
        with self._lock:
            if self._attempted:
                return self.health()
            self._attempted = True
            try:
                bundle = self._validate_artifacts()
                pipeline = HybridPipeline(
                    self.root, bundle, device=config.MODEL_DEVICE,
                    cpu_threads=config.MODEL_CPU_THREADS,
                    allowed_unexpected_encoder_keys=set(self.profile["allowed_unexpected_encoder_keys"]),
                )
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
            "name": self._model_name, "classifier": Path(self.profile["classifier"]).name,
            "profile": self.profile_id, "version": self.profile_id,
            "training_run_id": self.profile_id, "sha256": self._hash,
            "expected_sha256": self.profile["classifier_sha256"],
            "device": self._device, "feature_mode": "hybrid_distilbert",
            "decision_threshold": self._threshold, "label_mapping": LABEL_MAPPING,
            "runtime_versions": self._versions, "error": self._error,
            "deployment_approved": bool(self.profile["deployment_approved"]),
            "local_trial": not bool(self.profile["deployment_approved"]),
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
                threshold = float(self._pipeline.bundle["threshold"])
                results = []
                for score, values, chunk_count, token_count in zip(scores, features, chunks, tokens):
                    label = int(score >= threshold)
                    name = "Misleading" if label else "Non-Misleading"
                    display_label = "Potentially Misleading" if label else "No Misleading Information Detected"
                    results.append(Prediction(
                        internal_label=name, public_label=display_label,
                        confidence=float(score if label else 1 - score), model_status="ready",
                        model_name=self._model_name, model_version=self.profile_id,
                        model_score=float(score), predicted_class=label,
                        decision_threshold=threshold, training_run_id=self.profile_id,
                        artifact_sha256=self._hash, device=self._device,
                        chunk_count=int(chunk_count), content_token_count=int(token_count),
                        linguistic_indicators=[
                            {"name": feature_name, "value": float(value)}
                            for feature_name, value in zip(FEATURE_NAMES, values)
                        ],
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
    raise ModelUnavailableError(
        f"Model switching is disabled; the selected profile exposes only {Path(ACTIVE_PROFILE['classifier']).name}."
    )
