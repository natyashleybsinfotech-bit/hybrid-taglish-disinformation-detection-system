"""
src/taglish_filter.py — Stage 2b: Filter the corpus for Taglish content.
Input:  raw DataFrame with columns [text, label].
Output: filtered DataFrame containing only rows with both Filipino and English tokens.
"""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


# Build a set for O(1) lookup
_FILIPINO_SET = set(config.FILIPINO_PARTICLES)

# Common English stop words to help detect English presence
_ENGLISH_MARKERS = {
    "the", "is", "are", "was", "were", "been", "be", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "shall", "may",
    "might", "can", "must", "a", "an", "and", "or", "but", "not", "no",
    "in", "on", "at", "to", "for", "of", "with", "from", "by", "as",
    "it", "its", "this", "that", "these", "those", "he", "she", "they",
    "we", "you", "i", "me", "my", "your", "his", "her", "our", "their",
    "what", "which", "who", "whom", "how", "when", "where", "why",
    "if", "then", "than", "so", "very", "just", "about", "also",
    "news", "report", "said", "government", "president", "people",
    "country", "health", "public", "police", "city", "because",
    "after", "before", "during", "through", "between", "into",
    "fake", "true", "false", "real", "share", "post", "video", "photo",
}


def is_taglish(text: str) -> bool:
    """
    Return True if the text contains at least one Filipino particle
    AND at least one English marker word.
    """
    if not isinstance(text, str) or len(text.strip()) == 0:
        return False

    tokens = text.lower().split()
    has_filipino = any(t in _FILIPINO_SET for t in tokens)
    has_english = any(t in _ENGLISH_MARKERS for t in tokens)

    return has_filipino and has_english


def filter_taglish(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the Taglish filter and return only matching rows."""
    print("[taglish_filter] Filtering for Taglish content...")
    before = len(df)

    # Automatically find the text column (could be 'text' or 'article')
    text_col = "text" if "text" in df.columns else "article"
    if text_col not in df.columns:
        raise KeyError(f"Could not find text column. Available columns: {list(df.columns)}")

    mask = df[text_col].apply(is_taglish)
    filtered = df[mask].copy().reset_index(drop=True)

    after = len(filtered)
    discarded = before - after
    print(f"[taglish_filter] Retained: {after}  |  Discarded: {discarded}")
    
    # Ensure label column exists
    if "label" in filtered.columns:
        print(f"[taglish_filter] Label distribution after filtering:")
        print(f"{filtered['label'].value_counts().to_string()}")

    return filtered


if __name__ == "__main__":
    raw = pd.read_csv(config.RAW_DATA_PATH)
    filter_taglish(raw)
