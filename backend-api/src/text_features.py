"""Exact saved seven-feature measurements, independent of classifier inference."""
from functools import lru_cache
import hashlib
import json
import math
from threading import Lock
import config
try:
    from .hybrid_pipeline import HybridPipeline, FEATURE_NAMES, prepare_text
except ImportError:
    from hybrid_pipeline import HybridPipeline, FEATURE_NAMES, prepare_text

_lock = Lock()
_measurer = None

class TextFeatureMeasurer:
    # Reuse the exact measurement formula, without constructing its encoder/LR pipeline.
    linguistic_features = HybridPipeline.linguistic_features

    def __init__(self):
        import spacy
        from lingua import Language, LanguageDetectorBuilder
        root = config.MODEL_ARTIFACT_DIR or config.BASE_DIR / 'models' / 'TRAINING RESULTS'
        definitions = json.loads((root / 'models' / 'feature_config.json').read_text(encoding='utf8'))
        tokenizer = root / 'models' / 'tagalog_tokenizer'
        expected = definitions.get('calamancy_tokenizer_sha256')
        if not expected or hashlib.sha256(tokenizer.read_bytes()).hexdigest() != expected:
            raise ValueError('Saved feature tokenizer checksum does not match')
        self.nlp = spacy.blank('tl')
        self.nlp.tokenizer.from_disk(tokenizer, exclude=['vocab'])
        self.language = Language
        self.detector = LanguageDetectorBuilder.from_languages(Language.TAGALOG, Language.ENGLISH).with_minimum_relative_distance(.2).build()
        self.token_language = lru_cache(maxsize=4096)(self.detector.detect_language_of)
        lexicons = definitions['lexicons']
        self.particles = set(lexicons['particles']); self.emotion = set(lexicons['emotion']); self.urgency = set(lexicons['urgency'])

def measure_text_features(text):
    global _measurer
    prepared = prepare_text(text)
    with _lock:
        if _measurer is None: _measurer = TextFeatureMeasurer()
        values = _measurer.linguistic_features(prepared)
    if len(values) != len(FEATURE_NAMES) or any(not math.isfinite(float(v)) or not 0<=float(v)<=1 for v in values):
        raise ValueError('Invalid linguistic measurement')
    return [{'name':name,'value':float(value)} for name,value in zip(FEATURE_NAMES,values)]
