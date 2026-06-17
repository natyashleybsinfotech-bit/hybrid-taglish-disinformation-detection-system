import sys
import os
import joblib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
import config
from database import log_model

def main():
    print("Loading current model...")
    bundle = joblib.load(config.MODEL_PATH)
    metrics = bundle["meta"]["metrics"]
    best_name = bundle["meta"]["best"]
    conf = bundle["meta"].get("conf", {"tp": 0, "tn": 0, "fp": 0, "fn": 0})

    print("Logging model to database...")
    log_model(
        model_name="Hybrid DistilBERT + LR" if best_name == "hybrid" else "DistilBERT-only + LR",
        model_type=best_name,
        accuracy=metrics.get("acc", metrics.get("accuracy", 0.0)),
        precision_macro=metrics.get("precision", 0.0),
        recall_macro=metrics.get("recall", 0.0),
        f1_macro=metrics.get("f1", 0.0),
        avg_inference_ms=metrics.get("time", metrics.get("inference_ms", 0.0)),
        file_path=config.MODEL_PATH,
        conf_tp=conf["tp"],
        conf_tn=conf["tn"],
        conf_fp=conf["fp"],
        conf_fn=conf["fn"],
    )
    print("Done!")

if __name__ == "__main__":
    main()
