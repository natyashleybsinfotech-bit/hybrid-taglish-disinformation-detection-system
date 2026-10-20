"""
src/data_loader.py — Stage 2a: Load the Fake News Filipino corpus from HuggingFace.
Input:  nothing (downloads from the internet on first run, cached afterwards).
Output: pandas DataFrame saved to data/raw/corpus.csv with columns [text, label].
"""

import os
import sys
import pandas as pd
from datasets import load_dataset

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def load_corpus() -> pd.DataFrame:
    """Download the Fake News Filipino dataset and return it as a DataFrame."""
    print("[data_loader] Downloading corpus from HuggingFace...")
    ds = load_dataset("jcblaise/fake_news_filipino")

    # The dataset has a 'train' and 'validation' split — combine them
    frames = []
    for split_name in ds:
        frames.append(ds[split_name].to_pandas())
    df = pd.concat(frames, ignore_index=True)

    # Keep only the columns we need and rename for consistency
    df = df[["article", "label"]].copy()
    df.rename(columns={"article": "text"}, inplace=True)

    print(f"[data_loader] Total samples loaded: {len(df)}")
    print(f"[data_loader] Label distribution:\n{df['label'].value_counts().to_string()}")
    print(f"    Label 0 = Real (Non-Disinformation)")
    print(f"    Label 1 = Fake (Disinformation)")

    # Save to disk
    os.makedirs(os.path.dirname(config.RAW_DATA_PATH), exist_ok=True)
    df.to_csv(config.RAW_DATA_PATH, index=False)
    print(f"[data_loader] Saved raw corpus to {config.RAW_DATA_PATH}")

    return df


if __name__ == "__main__":
    load_corpus()
