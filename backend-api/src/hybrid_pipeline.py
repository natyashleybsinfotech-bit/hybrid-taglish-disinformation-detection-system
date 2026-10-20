"""Inference-only reproduction of notebook cells 9, 11, 13 and 19.

Only components from the hash-verified model_4 bundle are accepted. There is no
fitting, classifier selection, prediction cache or test-record access here.
"""

from functools import lru_cache
import re
import time
import config

import numpy as np

FEATURE_NAMES = (
    "code_switching_ratio", "filipino_particle_frequency", "punctuation_intensity",
    "capitalization_ratio", "repeated_character_ratio", "emotional_language_frequency",
    "urgency_cue_frequency",
)


def prepare_text(text: str) -> str:
    if not isinstance(text, str):
        raise ValueError("Text must be a string.")
    return re.sub(r"\s+", " ", text).strip()


class HybridPipeline:
    def __init__(self, root, bundle, *, device="auto", cpu_threads=4):
        import spacy
        import torch
        from lingua import Language, LanguageDetectorBuilder
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        if device not in {"auto", "cpu", "cuda"}:
            raise ValueError("SURI_MODEL_DEVICE must be auto, cpu or cuda")
        if device == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA was explicitly requested but is unavailable")
        self.device = "cuda" if device != "cpu" and torch.cuda.is_available() else "cpu"
        if self.device == "cpu":
            torch.set_num_threads(max(1, cpu_threads))
        encoder_dir = root / "models" / "contextual_encoder"
        self.tokenizer = AutoTokenizer.from_pretrained(encoder_dir, local_files_only=True)
        encoder, loading = AutoModel.from_pretrained(
            encoder_dir, local_files_only=True, use_safetensors=True, output_loading_info=True,
        )
        if any(loading.get(key) for key in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")):
            raise ValueError("Saved encoder weights did not load completely; refusing initialized or mismatched parameters")
        self.encoder = encoder.to(self.device)
        self.encoder.eval()
        for parameter in self.encoder.parameters():
            parameter.requires_grad_(False)
        if self.encoder.config.model_type != "distilbert" or self.encoder.config.dim != 768:
            raise ValueError("Expected the saved 768-dimensional multilingual DistilBERT encoder")
        if self.encoder.config.max_position_embeddings != 512 or self.tokenizer.num_special_tokens_to_add(pair=False) != 2:
            raise ValueError("Encoder/tokenizer window is incompatible with the saved 510-token chunk contract")
        self.nlp = spacy.blank("tl")
        self.nlp.tokenizer.from_disk(root / "models" / "tagalog_tokenizer", exclude=["vocab"])
        self.language = Language
        self.detector = LanguageDetectorBuilder.from_languages(Language.TAGALOG, Language.ENGLISH).with_minimum_relative_distance(.2).build()
        self.token_language = lru_cache(maxsize=100000)(self.detector.detect_language_of)
        lexicons = bundle["feature_config"]["lexicons"]
        self.particles = set(lexicons["particles"])
        self.emotion = set(lexicons["emotion"])
        self.urgency = set(lexicons["urgency"])
        self.bundle = bundle
        self.batch_size = bundle["encoder_settings"]["batch_size"]

    def linguistic_features(self, text):
        tokens = [t.text for t in self.nlp.make_doc(text) if not t.is_space]
        words = [t.casefold() for t in tokens if t.isalpha()]
        total, chars = len(tokens), len(text)
        counts = {self.language.TAGALOG: 0, self.language.ENGLISH: 0}
        for word in words:
            language = self.token_language(word)
            if language in counts:
                counts[language] += 1
        ft, en = counts[self.language.TAGALOG], counts[self.language.ENGLISH]
        alphabetic = [c for c in text if c.isalpha()]
        repeated = sum(len(match.group(0)) for match in re.finditer(r"(.)\1{2,}", text))
        def ratio(a, b):
            return a / b if b else 0.0
        return np.array([
            ratio(min(ft, en), ft + en),
            ratio(sum(w in self.particles for w in words), total),
            ratio(text.count("!") + text.count("?"), chars),
            ratio(sum(c.isupper() for c in alphabetic), len(alphabetic)),
            ratio(repeated, chars),
            ratio(sum(w in self.emotion for w in words), total),
            ratio(sum(w in self.urgency for w in words), total),
        ], dtype=np.float32)

    def embed_texts(self, texts):
        deadline = time.monotonic() + config.INFERENCE_TIMEOUT_SECONDS
        chunks, owners, per_record = [], [], []
        for index, text in enumerate(texts):
            ids = self.tokenizer(text, add_special_tokens=False, truncation=False, verbose=False)["input_ids"]
            if not ids:
                raise ValueError("Empty tokenizer output")
            parts = [ids[start:start + 510] for start in range(0, len(ids), 510)]
            per_record.append(len(parts))
            for part in parts:
                encoded = self.tokenizer.prepare_for_model(
                    part, add_special_tokens=True, return_attention_mask=True,
                    return_special_tokens_mask=False, truncation=False,
                )
                if encoded["input_ids"] != [self.tokenizer.cls_token_id] + part + [self.tokenizer.sep_token_id]:
                    raise ValueError("Unexpected DistilBERT special-token layout")
                # Added CLS/SEP are excluded, content tokens (including UNK) retained.
                encoded["special_tokens_mask"] = [1] + [0] * len(part) + [1]
                chunks.append(encoded)
                owners.append(index)
        sums = np.zeros((len(texts), 768), dtype=np.float64)
        totals = np.zeros(len(texts), dtype=np.int64)
        with self.torch.inference_mode():
            for start in range(0, len(chunks), self.batch_size):
                if time.monotonic() > deadline:
                    raise TimeoutError("Full-text inference exceeded the processing time limit; no partial prediction was produced")
                batch = self.tokenizer.pad(chunks[start:start + self.batch_size], padding=True, return_tensors="pt")
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
        if time.monotonic() > deadline:
            raise TimeoutError("Full-text inference exceeded the processing time limit; no partial prediction was produced")
        if not (totals > 0).all():
            raise ValueError("No content tokens after masking")
        return (sums / totals[:, None]).astype(np.float32), per_record, totals

    def infer(self, prepared_texts):
        embeddings, chunks, tokens = self.embed_texts(prepared_texts)
        linguistic = np.vstack([self.linguistic_features(text) for text in prepared_texts])
        matrix = np.hstack([
            self.bundle["context_scaler"].transform(embeddings),
            self.bundle["ling_scaler"].transform(linguistic),
        ])
        if matrix.shape != (len(prepared_texts), 775) or not np.isfinite(matrix).all():
            raise ValueError("Invalid hybrid feature matrix")
        classifier = self.bundle["classifier"]
        probabilities = np.asarray(classifier.predict_proba(matrix))
        if probabilities.shape != (len(prepared_texts), 2) or not np.isfinite(probabilities).all() or np.any(probabilities < 0) or np.any(probabilities > 1) or not np.allclose(probabilities.sum(axis=1), 1):
            raise ValueError("Invalid classifier probabilities")
        positive = list(classifier.classes_).index(1)
        return probabilities[:, positive], linguistic, chunks, tokens
