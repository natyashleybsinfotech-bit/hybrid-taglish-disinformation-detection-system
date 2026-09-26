"""MySQL/MariaDB persistence for the Sprint 1 SuriPH prototype."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Any

import mysql.connector
from mysql.connector import Error

import config


MIGRATIONS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (
        1,
        (
            """
            CREATE TABLE IF NOT EXISTS AdminUsers (
                admin_user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                username VARCHAR(80) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(40) NOT NULL DEFAULT 'admin',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login_at DATETIME NULL,
                PRIMARY KEY (admin_user_id),
                UNIQUE KEY uq_admin_users_username (username)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS CandidateSamples (
                candidate_sample_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                text_content TEXT NOT NULL,
                page_url TEXT NULL,
                page_title VARCHAR(500) NULL,
                source_type VARCHAR(40) NOT NULL DEFAULT 'browser-extension',
                language VARCHAR(40) NULL,
                topic VARCHAR(120) NULL,
                claim_group_id VARCHAR(120) NULL,
                proposed_label VARCHAR(40) NULL,
                validation_status VARCHAR(40) NOT NULL DEFAULT 'pending',
                training_status VARCHAR(40) NOT NULL DEFAULT 'not_training_data',
                submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (candidate_sample_id),
                KEY idx_candidate_status_date (validation_status, submitted_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
            """
            CREATE TABLE IF NOT EXISTS AuditLogs (
                audit_log_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                action VARCHAR(100) NOT NULL,
                description TEXT NULL,
                performed_by VARCHAR(80) NOT NULL DEFAULT 'system',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (audit_log_id),
                KEY idx_audit_action_date (action, created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """,
        ),
    ),
    (
        2,
        (
            "ALTER TABLE CandidateSamples ADD COLUMN IF NOT EXISTS "
            "training_status VARCHAR(40) NOT NULL DEFAULT 'not_training_data'",
        ),
    ),
)


def is_configured() -> bool:
    return bool(config.DB_HOST and config.DB_USER and config.DB_NAME)


def _connect():
    if not is_configured():
        raise RuntimeError("Database credentials are not configured.")
    return mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        connection_timeout=config.DB_CONNECT_TIMEOUT,
        autocommit=False,
    )


def database_health() -> dict[str, Any]:
    if not is_configured():
        return {"status": "not_configured", "engine": "mysql-mariadb"}
    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        connection.close()
        return {"status": "available", "engine": "mysql-mariadb"}
    except (Error, RuntimeError):
        return {"status": "unavailable", "engine": "mysql-mariadb"}


def migrate() -> dict[str, Any]:
    """Apply ordered migrations and return a non-sensitive status object."""
    if not is_configured():
        return {"status": "not_configured", "applied_versions": []}
    connection = None
    try:
        connection = _connect()
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS SchemaMigrations (
                version INT NOT NULL,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (version)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )
        cursor.execute("SELECT version FROM SchemaMigrations")
        applied = {int(row[0]) for row in cursor.fetchall()}
        newly_applied: list[int] = []
        for version, statements in MIGRATIONS:
            if version in applied:
                continue
            for statement in statements:
                cursor.execute(statement)
            cursor.execute("INSERT INTO SchemaMigrations (version) VALUES (%s)", (version,))
            newly_applied.append(version)
        connection.commit()
        cursor.close()
        connection.close()
        return {"status": "available", "applied_versions": newly_applied}
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
            connection.close()
        return {"status": "unavailable", "applied_versions": []}


def hash_password(password: str, *, iterations: int = 260_000) -> str:
    if not password:
        raise ValueError("Password cannot be empty.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations_text)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (TypeError, ValueError):
        return False


def ensure_bootstrap_admin() -> bool:
    username = config.ADMIN_BOOTSTRAP_USERNAME
    password = config.ADMIN_BOOTSTRAP_PASSWORD
    if not username or not password:
        return False
    connection = _connect()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT admin_user_id FROM AdminUsers WHERE username = %s", (username,))
    existing = cursor.fetchone()
    if existing:
        cursor.close()
        connection.close()
        return False
    cursor.execute(
        "INSERT INTO AdminUsers (username, password_hash, role) VALUES (%s, %s, 'admin')",
        (username, hash_password(password)),
    )
    connection.commit()
    cursor.close()
    connection.close()
    return True


def verify_admin(username: str, password: str) -> dict[str, Any] | None:
    connection = _connect()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT admin_user_id, username, password_hash, role FROM AdminUsers "
        "WHERE username = %s AND is_active = TRUE",
        (username,),
    )
    row = cursor.fetchone()
    if row and verify_password(password, row["password_hash"]):
        cursor.execute(
            "UPDATE AdminUsers SET last_login_at = CURRENT_TIMESTAMP WHERE admin_user_id = %s",
            (row["admin_user_id"],),
        )
        connection.commit()
    cursor.close()
    connection.close()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return {"id": row["admin_user_id"], "username": row["username"], "role": row["role"]}


def create_candidate(*, text: str, page_url: str | None, page_title: str | None) -> int:
    connection = _connect()
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO CandidateSamples (text_content, page_url, page_title)
        VALUES (%s, %s, %s)
        """,
        (text, page_url, page_title),
    )
    candidate_id = int(cursor.lastrowid)
    connection.commit()
    cursor.close()
    connection.close()
    return candidate_id


def list_candidates(limit: int = 100) -> list[dict[str, Any]]:
    connection = _connect()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM CandidateSamples ORDER BY submitted_at DESC LIMIT %s", (limit,)
    )
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return [_serialize_dates(row) for row in rows]


def log_audit(action: str, description: str, performed_by: str = "system") -> int:
    connection = _connect()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO AuditLogs (action, description, performed_by) VALUES (%s, %s, %s)",
        (action, description, performed_by),
    )
    audit_id = int(cursor.lastrowid)
    connection.commit()
    cursor.close()
    connection.close()
    return audit_id


def list_audits(limit: int = 100) -> list[dict[str, Any]]:
    connection = _connect()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM AuditLogs ORDER BY created_at DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()
    cursor.close()
    connection.close()
    return [_serialize_dates(row) for row in rows]


def sprint_stats() -> dict[str, int]:
    connection = _connect()
    cursor = connection.cursor(dictionary=True)
    cursor.execute(
        "SELECT COUNT(*) total, SUM(validation_status = 'pending') pending FROM CandidateSamples"
    )
    candidates = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) total FROM AuditLogs")
    audits = cursor.fetchone()
    cursor.close()
    connection.close()
    return {
        "candidate_samples": int(candidates["total"] or 0),
        "pending_candidates": int(candidates["pending"] or 0),
        "audit_events": int(audits["total"] or 0),
    }


def _serialize_dates(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in row.items()
    }


def init_db() -> bool:
    """Legacy compatibility wrapper; startup remains non-fatal when unavailable."""
    return migrate()["status"] == "available"


def log_model(*_args, **_kwargs):
    raise RuntimeError("Final model training is outside Sprint 1.")
