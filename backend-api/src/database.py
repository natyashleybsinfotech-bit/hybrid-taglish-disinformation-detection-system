"""
database.py — MySQL database functions for the Taglish Disinformation Detection System.
Connects to taglish_db on localhost via XAMPP (root, no password).
"""
import mysql.connector
from mysql.connector import Error
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "taglish_db",
}

def _get_connection():
    """Create and return a MySQL connection. Connects to server first to create DB if needed."""
    import time as _time
    max_attempts = 5
    attempt = 0
    last_err = None
    while attempt < max_attempts:
        try:
            # Connect without database first to ensure it exists
            conn = mysql.connector.connect(
                host=DB_CONFIG["host"],
                user=DB_CONFIG["user"],
                password=DB_CONFIG["password"]
            )
            cur = conn.cursor()
            cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
            cur.close()
            conn.close()

            # Connect to the specific database
            return mysql.connector.connect(**DB_CONFIG)
        except Error as e:
            last_err = e
            attempt += 1
            wait = 1 + attempt
            print(f"[database] Connection attempt {attempt}/{max_attempts} failed: {e}. Retrying in {wait}s...")
            _time.sleep(wait)

    # If we get here, all attempts failed
    print(f"[database] Connection error after {max_attempts} attempts: {last_err}")
    raise last_err

def init_db():
    """Create the 3 required tables if they do not exist."""
    conn = _get_connection()
    cur = conn.cursor()
    # 1. tblUsers
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tblUsers (
            user_id INT NOT NULL AUTO_INCREMENT,
            username VARCHAR(50) NOT NULL,
            password VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            role VARCHAR(20),
            is_active TINYINT(1) DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME,
            PRIMARY KEY (user_id),
            UNIQUE KEY uq_username (username)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 2. tblModels (include confusion matrix fields expected by the app)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tblModels (
            model_id INT NOT NULL AUTO_INCREMENT,
            model_name VARCHAR(100) NOT NULL,
            model_type VARCHAR(50) NOT NULL,
            accuracy FLOAT,
            precision_macro FLOAT,
            recall_macro FLOAT,
            f1_macro FLOAT,
            avg_inference_ms FLOAT,
            file_path VARCHAR(255),
            is_active TINYINT(1) DEFAULT 1,
            conf_tp INT DEFAULT 0,
            conf_tn INT DEFAULT 0,
            conf_fp INT DEFAULT 0,
            conf_fn INT DEFAULT 0,
            trained_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (model_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 3. tblPredictions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tblPredictions (
            pred_id INT NOT NULL AUTO_INCREMENT,
            user_id INT DEFAULT NULL,
            input_text TEXT NOT NULL,
            predicted_label TINYINT NOT NULL,
            label_text VARCHAR(30) NOT NULL,
            confidence FLOAT NOT NULL,
            cs_ratio FLOAT,
            urgency_count INT,
            particle_count INT,
            punct_intensity FLOAT,
            caps_ratio FLOAT,
            repeat_chars INT,
            emotional_count INT,
            inference_ms FLOAT,
            model_id INT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (pred_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # 4. tblActivityLog
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tblActivityLog (
            log_id INT NOT NULL AUTO_INCREMENT,
            user_id INT DEFAULT NULL,
            action VARCHAR(100) NOT NULL,
            description TEXT,
            performed_by VARCHAR(50) DEFAULT 'system',
            ip_address VARCHAR(45),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (log_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    
    conn.commit()
    
    # Ensure default admin exists and is correct
    cur.execute("SELECT user_id, password, is_active FROM tblUsers WHERE username = 'admin'")
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO tblUsers (username, password, role, is_active) VALUES ('admin', 'admin123', 'admin', 1)")
        conn.commit()
        print("[database] Default admin created (admin/admin123)")
    else:
        # If admin exists but password is wrong or it's inactive, fix it
        if row[1] != 'admin123' or row[2] == 0:
            cur.execute("UPDATE tblUsers SET password = 'admin123', is_active = 1 WHERE username = 'admin'")
            conn.commit()
            print("[database] Default admin credentials/status restored")

    cur.close()
    conn.close()
    print("[database] Tables initialized successfully.")

# ── User Management ──────────────────────────────────────────────────────

def verify_user(username, password):
    """Check if username and password match a row in tblUsers."""
    sql = "SELECT * FROM tblUsers WHERE username = %s AND password = %s AND is_active = 1"
    try:
        conn = _get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, (username, password))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
    except Error as e:
        print(f"[database] verify_user error: {e}")
        return None

def create_user(username, password, full_name=None, role='admin'):
    """Insert a new user into tblUsers."""
    sql = "INSERT INTO tblUsers (username, password, full_name, role) VALUES (%s, %s, %s, %s)"
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(sql, (username, password, full_name, role))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Error as e:
        print(f"[database] create_user error: {e}")
        return False

# ── Prediction Logging ──────────────────────────────────────────────────

def log_prediction(
    input_text,
    label,
    label_code,
    confidence,
    inference_ms,
    code_switching_ratio,
    urgency_count,
    particle_count,
    punctuation_intensity,
    caps_ratio,
    repeated_chars,
    emotional_count,
):
    """Insert one prediction row into tblPredictions."""
    sql = """
        INSERT INTO tblPredictions
            (input_text, label_text, predicted_label, confidence, inference_ms,
             cs_ratio, urgency_count, particle_count,
             punct_intensity, caps_ratio, repeat_chars, emotional_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(sql, (
            input_text, label, label_code, confidence, inference_ms,
            code_switching_ratio, urgency_count, particle_count,
            punctuation_intensity, caps_ratio, repeated_chars, emotional_count,
        ))
        conn.commit()
        row_id = cur.lastrowid
        cur.close()
        conn.close()
        return row_id
    except Error as e:
        print(f"[database] log_prediction error: {e}")
        return None

def get_predictions(limit=200):
    """Fetch recent predictions, newest first."""
    sql = "SELECT * FROM tblPredictions ORDER BY created_at DESC LIMIT %s"
    try:
        conn = _get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for row in rows:
            # Normalize field names expected by frontend
            if "pred_id" in row:
                row["id"] = row.get("pred_id")
            # Map DB columns to UI-friendly keys
            if "label_text" in row:
                row["label"] = row.get("label_text")
            if "predicted_label" in row:
                row["label_code"] = row.get("predicted_label")
            if "cs_ratio" in row:
                row["code_switching_ratio"] = row.get("cs_ratio")
            if "punct_intensity" in row:
                row["punctuation_intensity"] = row.get("punct_intensity")
            if "repeat_chars" in row:
                row["repeated_chars"] = row.get("repeat_chars")
            # Ensure numeric fields are present
            for k in ("confidence", "code_switching_ratio", "punctuation_intensity", "caps_ratio", "repeated_chars", "inference_ms"):
                if k not in row or row[k] is None:
                    row[k] = 0
            if isinstance(row.get("created_at"), datetime):
                row["created_at"] = row["created_at"].isoformat()
        return rows
    except Error as e:
        print(f"[database] get_predictions error: {e}")
        return []

def get_stats():
    """Get aggregate prediction statistics for the dashboard."""
    sql = """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN predicted_label = 1 THEN 1 ELSE 0 END) AS disinfo_count,
            SUM(CASE WHEN predicted_label = 0 THEN 1 ELSE 0 END) AS non_disinfo_count,
            ROUND(AVG(confidence) * 100, 2) AS avg_confidence
        FROM tblPredictions
    """
    try:
        conn = _get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql)
        row = cur.fetchone()
        cur.close()
        conn.close()
        return {
            "total": row["total"] or 0,
            "disinfo_count": int(row["disinfo_count"] or 0),
            "non_disinfo_count": int(row["non_disinfo_count"] or 0),
            "avg_confidence": float(row["avg_confidence"] or 0),
        }
    except Error as e:
        print(f"[database] get_stats error: {e}")
        return {"total": 0, "disinfo_count": 0, "non_disinfo_count": 0, "avg_confidence": 0}

# ── Model Logging ───────────────────────────────────────────────────────

def log_model(
    model_name,
    model_type,
    accuracy,
    precision_macro,
    recall_macro,
    f1_macro,
    avg_inference_ms,
    file_path,
    conf_tp=0,
    conf_tn=0,
    conf_fp=0,
    conf_fn=0,
):
    """Insert one model training record into tblModels."""
    sql = """
        INSERT INTO tblModels
            (model_name, model_type, accuracy, precision_macro,
             recall_macro, f1_macro, avg_inference_ms, file_path,
             conf_tp, conf_tn, conf_fp, conf_fn)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(sql, (
            model_name, model_type, accuracy, precision_macro,
            recall_macro, f1_macro, avg_inference_ms, file_path,
            conf_tp, conf_tn, conf_fp, conf_fn
        ))
        conn.commit()
        row_id = cur.lastrowid
        cur.close()
        conn.close()
        print(f"[database] Logged model '{model_name}' (id={row_id})")
        return row_id
    except Error as e:
        print(f"[database] log_model error: {e}")
        return None

def get_models():
    """Fetch all model training records, newest first."""
    sql = "SELECT * FROM tblModels ORDER BY trained_at DESC"
    try:
        conn = _get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for row in rows:
            if isinstance(row.get("trained_at"), datetime):
                row["trained_at"] = row["trained_at"].isoformat()
            # Normalize keys for frontend: use `id` instead of `model_id`
            if "model_id" in row:
                row["id"] = row.get("model_id")
            # Ensure confusion matrix fields exist for the UI
            for k in ("conf_tp", "conf_tn", "conf_fp", "conf_fn"):
                if k not in row or row[k] is None:
                    row[k] = 0
            # Ensure numeric fields are not None to avoid UI NaN
            for k in ("accuracy", "precision_macro", "recall_macro", "f1_macro", "avg_inference_ms"):
                if k not in row or row[k] is None:
                    row[k] = 0
        return rows
    except Error as e:
        print(f"[database] get_models error: {e}")
        return []

def get_latest_model():
    """Fetch the most recent model record."""
    sql = "SELECT * FROM tblModels ORDER BY trained_at DESC LIMIT 1"
    try:
        conn = _get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql)
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and isinstance(row.get("trained_at"), datetime):
            row["trained_at"] = row["trained_at"].isoformat()
        # Normalize keys for frontend compatibility
        if row:
            if "model_id" in row:
                row["id"] = row.get("model_id")
            for k in ("conf_tp", "conf_tn", "conf_fp", "conf_fn"):
                if k not in row or row[k] is None:
                    row[k] = 0
            for k in ("accuracy", "precision_macro", "recall_macro", "f1_macro", "avg_inference_ms"):
                if k not in row or row[k] is None:
                    row[k] = 0
        return row
    except Error as e:
        print(f"[database] get_latest_model error: {e}")
        return None

# ── Activity Logging ────────────────────────────────────────────────────

def log_activity(action, description, performed_by='system', ip_address=None):
    """Log an action to the activity log."""
    sql = """
        INSERT INTO tblActivityLog
            (action, description, performed_by, ip_address)
        VALUES (%s, %s, %s, %s)
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute(sql, (action, description, performed_by, ip_address))
        conn.commit()
        row_id = cur.lastrowid
        cur.close()
        conn.close()
        return row_id
    except Error as e:
        print(f"[database] log_activity error: {e}")
        return None

def get_activity_log(limit=100):
    """Fetch recent activity logs, newest first."""
    sql = "SELECT * FROM tblActivityLog ORDER BY created_at DESC LIMIT %s"
    try:
        conn = _get_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for row in rows:
            if isinstance(row.get("created_at"), datetime):
                row["created_at"] = row["created_at"].isoformat()
        return rows
    except Error as e:
        print(f"[database] get_activity_log error: {e}")
        return []
