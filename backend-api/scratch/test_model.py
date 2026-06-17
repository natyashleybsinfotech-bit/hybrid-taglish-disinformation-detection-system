import sys
import os
import joblib
import numpy as np

# Add project root and src to path
BASE_DIR = r"c:\Users\Lenovo\Desktop\capstone-wtf\hybrid taglish-detector system\backend-api"
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "src"))

import config
from preprocessing import clean_text
from feature_extractor import extract_7_features
from embedding_extractor import embeddings_for

# Load model
hybrid_path = os.path.join(BASE_DIR, "models", "logistic_regression.joblib")
model = joblib.load(hybrid_path)

test_samples = [
    "Ang pangulo ay nagpunta sa Davao para sa isang pagtitipon.", # Likely non-disinfo
    "GRABE ITO! SHARE AGAD BAGO MATANGGAL! HINDI DAPAT MALAMAN ITO NG MGA TAO!", # Likely disinfo
    "Hello world",
    "Ang ganda ng umaga.",
    "BILI NA KAYO NG PRODUKTO NAMIN DAHIL ITO AY PINAKAMAHALAGANG SEKRETO NG MGA MAYAYAMAN!", # Likely disinfo
]

print(f"Testing model: {hybrid_path}")
print("-" * 30)

for text in test_samples:
    clean = clean_text(text)
    feats = extract_7_features(clean)
    emb = embeddings_for([clean])
    vector = np.hstack([emb[0], feats])
    
    pred = model.predict(vector.reshape(1, -1))[0]
    proba = model.predict_proba(vector.reshape(1, -1))[0]
    
    label = "Disinformation" if pred == 1 else "Non-Disinformation"
    print(f"Text: {text}")
    print(f"Prediction: {label} (Confidence: {max(proba):.4f})")
    print(f"Features: {feats}")
    print("-" * 30)
