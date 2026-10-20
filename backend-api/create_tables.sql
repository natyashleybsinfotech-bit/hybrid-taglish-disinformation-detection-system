-- Local SQLite reference schema only. Production uses MariaDB and the
-- authoritative versioned SQLAlchemy schema in src/database.py.

CREATE TABLE IF NOT EXISTS SchemaMigrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS AdminUsers (
    admin_user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'admin',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at TEXT NULL
);

CREATE TABLE IF NOT EXISTS CandidateSamples (
    candidate_sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
    text_content TEXT NOT NULL,
    page_url TEXT NULL,
    page_title TEXT NULL,
    source_type TEXT NOT NULL DEFAULT 'browser-extension',
    language TEXT NULL,
    topic TEXT NULL,
    topic_confidence REAL NULL,
    topic_review_status TEXT NOT NULL DEFAULT 'auto_suggested',
    claim_group_id TEXT NULL,
    proposed_label TEXT NOT NULL CHECK (proposed_label IN ('Misleading', 'Non-Misleading')),
    validation_status TEXT NOT NULL DEFAULT 'pending',
    training_status TEXT NOT NULL DEFAULT 'not_training_data',
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_candidate_status_date
ON CandidateSamples (validation_status, submitted_at);

CREATE TABLE IF NOT EXISTS AuditLogs (
    audit_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    description TEXT NULL,
    performed_by TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- The remaining production entities are EvidenceRecords, Annotations,
-- DatasetVersions, DatasetItems, ModelVersions, and TrainingRuns. Do not apply
-- this reference file to production. The explicit src.manage migration command is authoritative,
-- including schema v5 ResearchRecords. Runtime production accounts cannot perform DDL.

CREATE INDEX IF NOT EXISTS idx_audit_action_date
ON AuditLogs (action, created_at);
