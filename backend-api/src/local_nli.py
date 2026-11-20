"""Offline, bounded premise -> hypothesis reading; never a truth classifier.

Model installation is explicit via scripts/prepare_local_nli.py. Request-time
loading uses local_files_only=True and cannot download weights or call an API.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from threading import Lock
import config

_MODEL_ID = 'MoritzLaurer/mDeBERTa-v3-base-mnli-xnli'
_MODEL_REVISION = '8adb042d524ecd5c26d3e3ba0e3fbcf7e2d0864c'
_pipe = None
_load_error = None
_lock = Lock()
_inference_lock = Lock()
_THRESHOLDS_PATH = Path(__file__).with_name('local_nli_thresholds.json')


def thresholds():
    data = json.loads(_THRESHOLDS_PATH.read_text(encoding='utf-8'))
    if data['model_revision'] != _MODEL_REVISION:
        raise ValueError('NLI threshold/model revision mismatch')
    result = {name: float(data[name]) for name in ('entailment', 'contradiction')}
    if not all(math.isfinite(v) and 0.5 <= v <= 1.0 for v in result.values()):
        raise ValueError('Invalid NLI thresholds')
    return result


def _get_pipeline():
    global _pipe, _load_error
    if _pipe is not None:
        return _pipe
    with _lock:
        if _pipe is not None:
            return _pipe
        if _load_error is not None:
            raise RuntimeError('Local evidence model is unavailable; restart after preparation')
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
            import torch
            folder = config.LOCAL_NLI_MODEL_DIR
            tokenizer = AutoTokenizer.from_pretrained(str(folder), local_files_only=True)
            model = AutoModelForSequenceClassification.from_pretrained(
                str(folder), local_files_only=True, dtype=torch.float32,
                use_safetensors=True, trust_remote_code=False,
            )
            if set(str(v).lower() for v in model.config.id2label.values()) != {'entailment', 'neutral', 'contradiction'}:
                raise ValueError('Unexpected local NLI label mapping')
            model.eval()
            _pipe = pipeline('text-classification', model=model, tokenizer=tokenizer,
                             device=-1, top_k=None)
        except Exception as exc:
            _load_error = type(exc).__name__
            raise RuntimeError('Prepare the pinned local evidence model before use') from None
    return _pipe


def health():
    prepared = (config.LOCAL_NLI_MODEL_DIR / 'model.safetensors').is_file()
    return {'enabled': config.LOCAL_NLI_ENABLED, 'provider': 'local_nli',
            'model': _MODEL_ID, 'revision': _MODEL_REVISION,
            'status': 'disabled' if not config.LOCAL_NLI_ENABLED else 'unavailable' if _load_error else 'ready' if _pipe is not None else 'prepared' if prepared else 'not_prepared',
            'loaded': _pipe is not None, 'offline_inference': True,
            'thresholds': thresholds()}


def score_pairs(pairs):
    """Return all three model labels, preserving premise/hypothesis orientation."""
    if not pairs:
        return []
    pipe = _get_pipeline()
    for premise, hypothesis in pairs:
        # Do not silently discard material dates or the end of a claim.
        if len(pipe.tokenizer(premise, hypothesis, truncation=False)['input_ids']) > 512:
            raise ValueError('NLI pair exceeds token budget')
    with _inference_lock:
        output = pipe([{'text': p, 'text_pair': h} for p, h in pairs],
                      batch_size=4, truncation=False, max_length=512)
    scores = []
    for row in output:
        labels = {item['label'].lower(): float(item['score']) for item in row}
        if set(labels) != {'entailment', 'neutral', 'contradiction'} or not all(math.isfinite(v) and 0 <= v <= 1 for v in labels.values()):
            raise ValueError('Malformed local evidence output')
        scores.append(labels)
    return scores


def _windows(claim, body):
    terms = set(re.findall(r'[^\W_]+', claim.casefold()))
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', body) if s.strip()]
    candidates = []
    for i, sentence in enumerate(sentences):
        for width in (1, 2):
            parts = sentences[i:i+width]
            if len(parts) != width:
                continue
            passage = ' '.join(parts)
            if not 15 <= len(passage) <= 1400 or len(passage.split()) > 140:
                continue
            # A model must not turn a quote, question or conditional into fact.
            if any(s.startswith(('"', '“', "'", '‘', '>')) for s in parts) or '?' in passage:
                continue
            if re.search(r'\b(?:if|whether|would|could|might|kung|sakali|allegedly|umano|rumou?rs?|viral posts?|post claims?|claimed|says?|said|quoted?)\b', passage, re.I):
                continue
            overlap = len(terms & set(re.findall(r'[^\W_]+', passage.casefold())))
            if overlap < 2:
                continue
            candidates.append((-overlap, len(passage), i, passage))
    # The exact passages come from the supplied body. No generated citations.
    return list(dict.fromkeys(row[3] for row in sorted(candidates)))[:8]


def assess_relation(claim, body):
    """Conservative optional fallback; unavailable/uncertain remains related."""
    if not config.LOCAL_NLI_ENABLED:
        return 'related', 'Local semantic reading is disabled.'
    windows = _windows(claim, body)
    if not windows:
        return 'related', 'No bounded declarative article passage was available.'
    try:
        values = score_pairs([(passage, claim) for passage in windows])
        cutoffs = thresholds()
    except Exception:
        return 'related', 'Local semantic reading was unavailable or the text exceeded its budget.'
    accepted = []
    for passage, scores in zip(windows, values):
        winner = max(scores, key=scores.get)
        if winner in cutoffs and scores[winner] >= cutoffs[winner]:
            accepted.append(('supports' if winner == 'entailment' else 'contradicts', passage))
    if len({relation for relation, _ in accepted}) > 1:
        return 'conflicting', 'The article contains opposing assertions for the claim.'
    return accepted[0] if accepted else ('related', 'The local NLI scores did not pass the calibrated acceptance thresholds.')
