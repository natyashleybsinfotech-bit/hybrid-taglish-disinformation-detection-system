"""
preprocessing.py — Stage 3: text cleaning and tokenization helpers.
"""
import re
import sys
import os
from typing import List
import pandas as pd
try:
    import calamancy
    import spacy
    # Initialize the model (using the large model for best quality)
    # Note: We use the explicit version if calamancy.load has trouble resolving short names
    try:
        nlp = calamancy.load("tl_calamancy_lg-0.2.0")
    except Exception:
        # Fallback to direct spacy load if already installed
        nlp = spacy.load("tl_calamancy_lg")
    print("[preprocessing] CalamanCy (tl_calamancy_lg) loaded successfully.")
except Exception as e:
    nlp = None
    print(f"[preprocessing] CalamanCy or model not found. Using basic regex cleaning.")
    # Detailed error for debugging: print(f"Error: {e}")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_EMOJI_RE = re.compile("[\U00010000-\U0010ffff]", flags=re.UNICODE)


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    x = text
    x = _URL_RE.sub("", x)
    x = _EMOJI_RE.sub("", x)
    x = x.replace("\n", " ")
    x = re.sub(r"\s+", " ", x)
    x = x.strip()
    
    # ── Advanced CalamanCy Preprocessing ─────────────────────────────────
    if nlp:
        try:
            doc = nlp(x)
            # Use lemmatization to normalize Tagalog words
            x = " ".join([token.lemma_ for token in doc])
        except Exception as e:
            print(f"[preprocessing] CalamanCy error: {e}")
            
    return x


def dedupe_df(df: pd.DataFrame, text_col: str = "text") -> pd.DataFrame:
    before = len(df)
    out = df.drop_duplicates(subset=[text_col]).reset_index(drop=True)
    after = len(out)
    print(f"[preprocessing] Dropped {before-after} duplicates")
    return out


def preprocess_df(df: pd.DataFrame, text_col: str = "text") -> pd.DataFrame:
    df = dedupe_df(df, text_col=text_col)
    df["clean_text"] = df[text_col].astype(str).apply(clean_text)
    df = df[df["clean_text"].str.len() > 0].reset_index(drop=True)
    print(f"[preprocessing] Kept {len(df)} samples after cleaning")
    return df


def batch_texts(texts: List[str], batch_size: int = config.BATCH_SIZE):
    for i in range(0, len(texts), batch_size):
        yield texts[i : i + batch_size]
