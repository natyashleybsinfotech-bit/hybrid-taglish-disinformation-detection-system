"""
embedding_extractor.py — Stage 4 Track A: get DistilBERT CLS embeddings.
Optimised: model is loaded once at import time, device is cached, and
torch.no_grad() is always active so inference is as fast as possible.
"""
import sys
import os
from typing import List
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

# ── Load model once at module import (not lazily per-request) ────────────────
_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"[embedding_extractor] Loading DistilBERT on {_DEVICE}…")
_tokenizer = AutoTokenizer.from_pretrained(config.DISTILBERT_MODEL_NAME)
_model = AutoModel.from_pretrained(config.DISTILBERT_MODEL_NAME)
_model.eval()
_model.to(_DEVICE)
print("[embedding_extractor] DistilBERT ready.")


def embeddings_for(texts: List[str]) -> np.ndarray:
    """Return CLS embeddings as numpy array shape (n, hidden_size).
    Model and device are already loaded — no cold-start overhead."""
    all_embeds = []
    with torch.no_grad():
        for i in range(0, len(texts), config.BATCH_SIZE):
            batch = texts[i : i + config.BATCH_SIZE]
            enc = _tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=config.MAX_SEQ_LENGTH,
                return_tensors="pt",
            )
            enc = {k: v.to(_DEVICE) for k, v in enc.items()}
            out = _model(**enc)
            cls = out.last_hidden_state[:, 0, :].cpu().numpy()
            all_embeds.append(cls)
    return np.vstack(all_embeds)
