"""
train_model.py — Stage 5+7: build dataset, train LogisticRegression experiments,
evaluate, save models, and log metrics to MySQL database.
"""
import os
import sys
import time
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, StratifiedShuffleSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from imblearn.over_sampling import SMOTE

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
import config
from preprocessing import preprocess_df
from taglish_filter import filter_taglish
from feature_extractor import batch_extract
from embedding_extractor import embeddings_for
from database import log_model, init_db


# ── Model save paths (joblib format for the doc spec) ──────────────────
HYBRID_MODEL_PATH = os.path.join(config.BASE_DIR, "models", "logistic_regression.joblib")
DISTILBERT_ONLY_PATH = os.path.join(config.BASE_DIR, "models", "distilbert_only_lr.joblib")
# Also keep the legacy pkl bundle for backward compatibility
BUNDLE_PATH = config.MODEL_PATH  # models/hybrid_model.pkl


def load_and_prepare():
    # Allow the API to override the dataset path via environment variable
    dataset_path = os.environ.get("TAGLISH_DATASET_OVERRIDE") or config.RAW_DATA_PATH
    print(f"[train] Loading dataset from: {dataset_path}")
    df = pd.read_csv(dataset_path)

    # Standardize column name
    if "article" in df.columns and "text" not in df.columns:
        df = df.rename(columns={"article": "text"})

    df = filter_taglish(df)
    df = preprocess_df(df, text_col="text")
    texts = df["clean_text"].tolist()
    y = df["label"].values
    return texts, y


def build_features(texts):
    X_emb = embeddings_for(texts)
    X_feat = batch_extract(texts)
    X_hybrid = np.hstack([X_emb, X_feat])
    return X_emb, X_feat, X_hybrid


def measure_inference_ms(pipe, sample):
    """Measure average inference time in milliseconds over 100 runs."""
    sample_2d = sample.reshape(1, -1)
    # Warmup
    pipe.predict(sample_2d)
    # Timed runs
    times = []
    for _ in range(100):
        t0 = time.perf_counter()
        pipe.predict(sample_2d)
        t1 = time.perf_counter()
        times.append(t1 - t0)
    return np.mean(times) * 1000  # Convert to ms


def print_comparison_table(hybrid_metrics, embed_metrics):
    """Print a clean side-by-side comparison table to the console."""
    print()
    print("=" * 70)
    print("MODEL COMPARISON (Test Set)")
    print("=" * 70)
    print(f"{'Metric':<25} {'Hybrid DistilBERT+LR':>20} {'DistilBERT-only+LR':>20}")
    print("-" * 70)
    for key, label in [
        ("accuracy", "Accuracy"),
        ("precision", "Precision (macro)"),
        ("recall", "Recall (macro)"),
        ("f1", "F1 Score (macro)"),
        ("inference_ms", "Inference (ms)"),
    ]:
        h_val = hybrid_metrics[key]
        e_val = embed_metrics[key]
        if key == "inference_ms":
            print(f"{label:<25} {h_val:>19.2f}ms {e_val:>19.2f}ms")
        else:
            print(f"{label:<25} {h_val*100:>19.2f}% {e_val*100:>19.2f}%")
    print("=" * 70)
    print()


def main():
    init_db()
    print("[train] Loading and preparing data...")
    texts, y = load_and_prepare()
    X_emb, X_feat, X_hybrid = build_features(texts)

    # Stratified split 70/15/15 using consistent indices for all feature sets
    sss = StratifiedShuffleSplit(n_splits=1, train_size=config.TRAIN_RATIO, random_state=config.RANDOM_SEED)
    idx = list(sss.split(X_hybrid, y))[0]
    train_idx, temp_idx = idx[0], idx[1]

    val_frac = config.VAL_RATIO / (config.VAL_RATIO + config.TEST_RATIO)
    sss2 = StratifiedShuffleSplit(n_splits=1, train_size=val_frac, random_state=config.RANDOM_SEED)
    idx2 = list(sss2.split(X_hybrid[temp_idx], y[temp_idx]))[0]
    val_idx = temp_idx[idx2[0]]
    test_idx = temp_idx[idx2[1]]

    Xh_train, Xh_val, Xh_test = X_hybrid[train_idx], X_hybrid[val_idx], X_hybrid[test_idx]
    Xe_train, Xe_val, Xe_test = X_emb[train_idx], X_emb[val_idx], X_emb[test_idx]
    ytr, yv, yt = y[train_idx], y[val_idx], y[test_idx]

    # ── Apply SMOTE to handle class imbalance ─────────────────────────────
    print(f"[train] Applying SMOTE. Original distribution: {np.bincount(ytr)}")
    sm = SMOTE(random_state=config.RANDOM_SEED)
    Xh_train, ytr_h = sm.fit_resample(Xh_train, ytr)
    Xe_train, ytr_e = sm.fit_resample(Xe_train, ytr)
    print(f"[train] After SMOTE distribution: {np.bincount(ytr_h)}")

    # ── Train model ──────────────────────────────────────────────────────
    pipe_hybrid = Pipeline([("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))])
    
    print("[train] Training hybrid LogisticRegression (768 + 7 features)...")
    pipe_hybrid.fit(Xh_train, ytr_h)

    # ── Evaluate on validation ───────────────────────────────────────────
    print("\n[train] Evaluating on validation set...")
    preds = pipe_hybrid.predict(Xh_val)
    acc = accuracy_score(yv, preds)
    p = precision_score(yv, preds, average="macro", zero_division=0)
    r = recall_score(yv, preds, average="macro", zero_division=0)
    f1 = f1_score(yv, preds, average="macro", zero_division=0)
    print(f"  Hybrid (val): acc={acc:.4f}  p={p:.4f}  r={r:.4f}  f1={f1:.4f}")

    # ── Evaluate on test set + compute metrics for DB ────────────────────
    print("\n[train] Evaluating on test set...")

    h_preds = pipe_hybrid.predict(Xh_test)
    hybrid_metrics = {
        "accuracy": accuracy_score(yt, h_preds),
        "precision": precision_score(yt, h_preds, average="macro", zero_division=0),
        "recall": recall_score(yt, h_preds, average="macro", zero_division=0),
        "f1": f1_score(yt, h_preds, average="macro", zero_division=0),
        "inference_ms": measure_inference_ms(pipe_hybrid, Xh_test[0]),
    }
    print(f"  Hybrid (test): acc={hybrid_metrics['accuracy']:.4f}  f1={hybrid_metrics['f1']:.4f}  inference={hybrid_metrics['inference_ms']:.2f}ms")
    
    tn_h, fp_h, fn_h, tp_h = confusion_matrix(yt, h_preds).ravel()

    # ── Save models ──────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(HYBRID_MODEL_PATH), exist_ok=True)

    joblib.dump(pipe_hybrid, HYBRID_MODEL_PATH)
    print(f"[train] Saved hybrid model to {HYBRID_MODEL_PATH}")

    # Also save legacy bundle
    joblib.dump({"model": pipe_hybrid, "meta": {
        "best": "hybrid", 
        "metrics": hybrid_metrics,
        "conf": {
            "tp": int(tp_h),
            "tn": int(tn_h),
            "fp": int(fp_h),
            "fn": int(fn_h)
        }
    }}, BUNDLE_PATH)
    print(f"[train] Saved legacy bundle to {BUNDLE_PATH}")

    # ── Log to MySQL database ────────────────────────────────────────────
    print("\n[train] Logging metrics to database...")

    log_model(
        model_name="Hybrid Taglish Detector",
        model_type="hybrid",
        accuracy=hybrid_metrics["accuracy"],
        precision_macro=hybrid_metrics["precision"],
        recall_macro=hybrid_metrics["recall"],
        f1_macro=hybrid_metrics["f1"],
        avg_inference_ms=hybrid_metrics["inference_ms"],
        file_path="models/logistic_regression.joblib",
        conf_tp=int(tp_h),
        conf_tn=int(tn_h),
        conf_fp=int(fp_h),
        conf_fn=int(fn_h)
    )

    print("[train] Done! Hybrid model trained, saved, and logged to database.")


if __name__ == "__main__":
    main()
