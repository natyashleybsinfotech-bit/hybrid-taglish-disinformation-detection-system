"""
populate_sample_data.py — Populate the taglish_db with sample data for testing.
Run this once after creating the tables to fill the admin dashboard with data.
"""
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from database import (
    _get_connection,
    log_activity,
    log_model,
    log_prediction,
)

# Sample disinformation and non-disinformation texts
DISINFO_SAMPLES = [
    "BREAKING: COVID vaccine causes magnetic powers!!! Share before deleted!!!",
    "EXCLUSIVE: Politicians discovered to be ALIENS from outer space 👽👽",
    "FAKE NEWS: Election was rigged with 5G technology - PROOF INSIDE!",
    "DON'T LET THEM TELL YOU: Water fluoridation is mind control 🧠",
    "WARNING: Government tracking everyone through phones!!! 📱",
    "SHOCKING: Celebrities secretly sacrificing babies for power???",
    "MUST READ: Big Pharma hiding cure for all diseases!!!",
]

NON_DISINFO_SAMPLES = [
    "The weather today is expected to be sunny with temperatures around 28 degrees.",
    "New study shows regular exercise improves cardiovascular health.",
    "Local community organizes cleanup drive in neighborhood parks.",
    "Scientists discover new species of fish in the Amazon river.",
    "Government announces new scholarship program for underprivileged students.",
    "Tech company releases new software update with bug fixes and improvements.",
    "Report: Economy shows signs of steady growth this quarter.",
]

def populate_users():
    """Create sample users in tblUsers."""
    print("[populate] Creating sample users...")
    conn = _get_connection()
    cur = conn.cursor()
    
    users = [
        ("admin", "admin123", "Administrator", "admin"),
        ("john_doe", "pass123", "John Doe", "analyst"),
        ("jane_smith", "pass456", "Jane Smith", "analyst"),
        ("mike_wilson", "pass789", "Mike Wilson", "moderator"),
    ]
    
    for username, password, full_name, role in users:
        try:
            sql = "INSERT INTO tblUsers (username, password, full_name, role) VALUES (%s, %s, %s, %s)"
            cur.execute(sql, (username, password, full_name, role))
        except Exception as e:
            print(f"  - User {username} already exists or error: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print("[populate] Users created successfully.\n")

def populate_models():
    """Create sample model records in tblModels."""
    print("[populate] Creating sample models...")
    
    models = [
        ("Hybrid Model v1", "hybrid", 0.87, 0.85, 0.88, 0.86, 42.5, "/models/logistic_regression.joblib"),
        ("DistilBERT LR v1", "embedding", 0.84, 0.82, 0.85, 0.83, 58.3, "/models/distilbert_only_lr.joblib"),
        ("Hybrid Model v2", "hybrid", 0.91, 0.90, 0.92, 0.91, 41.2, "/models/logistic_regression_v2.joblib"),
    ]
    
    for model_name, model_type, accuracy, precision, recall, f1, avg_ms, file_path in models:
        try:
            log_model(model_name, model_type, accuracy, precision, recall, f1, avg_ms, file_path)
            print(f"  - Created model: {model_name}")
        except Exception as e:
            print(f"  - Error creating model {model_name}: {e}")
    
    print("[populate] Models created successfully.\n")

def populate_predictions():
    """Create sample prediction records in tblPredictions."""
    print("[populate] Creating sample predictions...")
    
    conn = _get_connection()
    cur = conn.cursor()
    
    # Get the latest model_id
    cur.execute("SELECT model_id FROM tblModels ORDER BY trained_at DESC LIMIT 1")
    result = cur.fetchone()
    model_id = result[0] if result else 1
    
    # Get user IDs
    cur.execute("SELECT user_id FROM tblUsers")
    user_ids = [row[0] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    # Generate sample predictions
    now = datetime.now()
    for i in range(50):
        # 40% disinformation, 60% non-disinformation
        is_disinfo = random.random() < 0.4
        
        text = random.choice(DISINFO_SAMPLES if is_disinfo else NON_DISINFO_SAMPLES)
        label = "Disinformation" if is_disinfo else "Non-Disinformation"
        label_code = 1 if is_disinfo else 0
        confidence = random.uniform(0.65, 0.99)
        
        # Features (random values)
        cs_ratio = random.uniform(0.1, 0.8)
        urgency_count = random.randint(0, 5) if is_disinfo else random.randint(0, 2)
        particle_count = random.randint(0, 10)
        punct_intensity = random.uniform(0.1, 0.9)
        caps_ratio = random.uniform(0.05, 0.7) if is_disinfo else random.uniform(0.01, 0.3)
        repeated_chars = random.randint(0, 8) if is_disinfo else random.randint(0, 2)
        emotional_count = random.randint(0, 5) if is_disinfo else random.randint(0, 2)
        inference_ms = random.uniform(15, 120)
        
        user_id = random.choice(user_ids) if random.random() > 0.3 else None
        
        try:
            log_prediction(
                input_text=text,
                label=label,
                label_code=label_code,
                confidence=confidence,
                inference_ms=inference_ms,
                code_switching_ratio=cs_ratio,
                urgency_count=urgency_count,
                particle_count=particle_count,
                punctuation_intensity=punct_intensity,
                caps_ratio=caps_ratio,
                repeated_chars=repeated_chars,
                emotional_count=emotional_count,
                user_id=user_id,
                model_id=model_id,
            )
        except Exception as e:
            print(f"  - Error creating prediction {i}: {e}")
    
    print(f"[populate] Created 50 sample predictions.\n")

def populate_activity_log():
    """Create sample activity log records in tblActivityLog."""
    print("[populate] Creating sample activity logs...")
    
    conn = _get_connection()
    cur = conn.cursor()
    
    # Get user IDs
    cur.execute("SELECT user_id FROM tblUsers")
    user_ids = [row[0] for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    activities = [
        ("SYSTEM_START", "FastAPI server started successfully", "system", None),
        ("ADMIN_LOGIN", "Admin logged in successfully", "admin", user_ids[0] if user_ids else None),
        ("PREDICTION", "Label: Disinformation, Confidence: 0.87", "end_user", None),
        ("MODEL_LOADED", "Hybrid model loaded from disk", "system", None),
        ("ADMIN_LOGOUT", "Admin logged out", "admin", user_ids[0] if user_ids else None),
        ("RETRAIN_STARTED", "Model retraining initiated", "admin", user_ids[0] if user_ids else None),
        ("PREDICTION", "Label: Non-Disinformation, Confidence: 0.92", "end_user", None),
    ]
    
    for action, description, performed_by, user_id in activities:
        try:
            log_activity(action, description, performed_by, None, user_id)
            print(f"  - Logged activity: {action}")
        except Exception as e:
            print(f"  - Error logging activity {action}: {e}")
    
    print("[populate] Activity logs created successfully.\n")

if __name__ == "__main__":
    print("=" * 60)
    print("Populating Sample Data for Taglish Disinformation Detector")
    print("=" * 60 + "\n")
    
    try:
        populate_users()
        populate_models()
        populate_predictions()
        populate_activity_log()
        
        print("=" * 60)
        print("✓ Sample data population completed successfully!")
        print("=" * 60)
        print("\nYou can now:")
        print("  1. Start the backend API: python src/app.py")
        print("  2. Navigate to the admin dashboard")
        print("  3. Login with: admin / admin123")
    except Exception as e:
        print(f"\n✗ Error during population: {e}")
        import traceback
        traceback.print_exc()
