"""SQLAlchemy persistence for MariaDB production and SQLite development/tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    inspect,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

import config

SCHEMA_VERSION = 5
metadata = MetaData()

schema_migrations = Table(
    "SchemaMigrations",
    metadata,
    Column("version", Integer, primary_key=True),
    Column("applied_at", DateTime, nullable=False, server_default=func.now()),
)
admin_users = Table(
    "AdminUsers",
    metadata,
    Column("admin_user_id", Integer, primary_key=True, autoincrement=True),
    Column("username", String(80), nullable=False, unique=True),
    Column("password_hash", String(255), nullable=False),
    Column("role", String(40), nullable=False, server_default="admin"),
    Column("is_active", Boolean, nullable=False, server_default="1"),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("last_login_at", DateTime, nullable=True),
)
candidate_samples = Table(
    "CandidateSamples",
    metadata,
    Column("candidate_sample_id", Integer, primary_key=True, autoincrement=True),
    Column("text_content", Text, nullable=False),
    Column("page_url", Text, nullable=True),
    Column("page_title", String(500), nullable=True),
    Column("source_type", String(40), nullable=False, server_default="browser-extension"),
    Column("language", String(40), nullable=True),
    Column("topic", String(120), nullable=True),
    Column("topic_confidence", Float, nullable=True),
    Column("topic_review_status", String(40), nullable=False, server_default="auto_suggested"),
    Column("claim_group_id", String(120), nullable=True),
    Column("proposed_label", String(40), nullable=False),
    Column("validation_status", String(40), nullable=False, server_default="pending"),
    Column("training_status", String(40), nullable=False, server_default="not_training_data"),
    Column("submitted_at", DateTime, nullable=False, server_default=func.now()),
)
Index("idx_candidate_status_date", candidate_samples.c.validation_status, candidate_samples.c.submitted_at)
audit_logs = Table(
    "AuditLogs",
    metadata,
    Column("audit_log_id", Integer, primary_key=True, autoincrement=True),
    Column("action", String(100), nullable=False),
    Column("description", Text, nullable=True),
    Column("performed_by", String(80), nullable=False, server_default="system"),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)
Index("idx_audit_action_date", audit_logs.c.action, audit_logs.c.created_at)
evidence_records = Table(
    "EvidenceRecords",
    metadata,
    Column("evidence_record_id", Integer, primary_key=True, autoincrement=True),
    Column("candidate_sample_id", Integer, ForeignKey("CandidateSamples.candidate_sample_id"), nullable=False),
    Column("source_url", Text, nullable=False),
    Column("publisher", String(200), nullable=True),
    Column("rating", String(120), nullable=True),
    Column("claim_match_status", String(40), nullable=False, server_default="unreviewed"),
    Column("reviewer_identifier", String(80), nullable=False),
    Column("notes", Text, nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)
annotations = Table(
    "Annotations",
    metadata,
    Column("annotation_id", Integer, primary_key=True, autoincrement=True),
    Column("candidate_sample_id", Integer, ForeignKey("CandidateSamples.candidate_sample_id"), nullable=False),
    Column("reviewer_identifier", String(80), nullable=False),
    Column("proposed_label", String(40), nullable=True),
    Column("decision", String(40), nullable=False),
    Column("annotation_round", String(40), nullable=False, server_default="reconciliation"),
    Column("is_independent", Boolean, nullable=False, server_default="0"),
    Column("evidence_sufficient", Boolean, nullable=True),
    Column("notes", Text, nullable=True),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
)
dataset_versions = Table(
    "DatasetVersions",
    metadata,
    Column("dataset_version_id", Integer, primary_key=True, autoincrement=True),
    Column("version_name", String(120), nullable=False, unique=True),
    Column("description", Text, nullable=True),
    Column("status", String(40), nullable=False, server_default="draft"),
    Column("created_by", String(80), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("approved_at", DateTime, nullable=True),
)
dataset_items = Table(
    "DatasetItems",
    metadata,
    Column("dataset_item_id", Integer, primary_key=True, autoincrement=True),
    Column("dataset_version_id", Integer, ForeignKey("DatasetVersions.dataset_version_id"), nullable=False),
    Column("candidate_sample_id", Integer, ForeignKey("CandidateSamples.candidate_sample_id"), nullable=False),
    Column("final_label", String(40), nullable=False),
    Column("partition_name", String(20), nullable=False),
    Column("claim_group_id", String(120), nullable=False),
    UniqueConstraint("dataset_version_id", "candidate_sample_id", name="uq_dataset_candidate"),
)
model_versions = Table(
    "ModelVersions",
    metadata,
    Column("model_version_id", Integer, primary_key=True, autoincrement=True),
    Column("dataset_version_id", Integer, ForeignKey("DatasetVersions.dataset_version_id"), nullable=False),
    Column("model_name", String(160), nullable=False),
    Column("version_name", String(120), nullable=False, unique=True),
    Column("feature_mode", String(80), nullable=False),
    Column("metrics_json", Text, nullable=False),
    Column("artifact_path", Text, nullable=False),
    Column("status", String(40), nullable=False, server_default="candidate"),
    Column("created_by", String(80), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("reviewed_by", String(80), nullable=True),
    Column("reviewed_at", DateTime, nullable=True),
    Column("activated_at", DateTime, nullable=True),
)
training_runs = Table(
    "TrainingRuns",
    metadata,
    Column("training_run_id", Integer, primary_key=True, autoincrement=True),
    Column("dataset_version_id", Integer, ForeignKey("DatasetVersions.dataset_version_id"), nullable=False),
    Column("requested_version_name", String(120), nullable=False),
    Column("status", String(40), nullable=False, server_default="queued"),
    Column("progress_percent", Integer, nullable=False, server_default="0"),
    Column("progress_stage", String(120), nullable=False, server_default="Queued"),
    Column("requested_by", String(80), nullable=False),
    Column("requested_at", DateTime, nullable=False, server_default=func.now()),
    Column("started_at", DateTime, nullable=True),
    Column("completed_at", DateTime, nullable=True),
    Column("error_message", Text, nullable=True),
    Column("model_version_id", Integer, ForeignKey("ModelVersions.model_version_id"), nullable=True),
)

research_records = Table(
    "ResearchRecords", metadata,
    Column("record_id", String(32), primary_key=True),
    Column("withdrawal_hash", String(64), nullable=False),
    Column("consent_version", String(40), nullable=False),
    Column("created_at", DateTime, nullable=False, server_default=func.now()),
    Column("expires_at", DateTime, nullable=False, index=True),
    Column("input_type", String(20), nullable=False),
    Column("text_content", Text, nullable=True),
    Column("result_json", Text, nullable=False),
    Column("evidence_json", Text, nullable=False),
    Column("usefulness", Integer, nullable=True),
)

_engine: Engine | None = None
_engine_key: str | None = None
_engine_lock = Lock()


def _database_url() -> URL | str | None:
    if config.DATABASE_URL:
        return config.DATABASE_URL
    if not config.DB_PATH:
        return None
    database_path = Path(config.DB_PATH)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return URL.create("sqlite", database=str(database_path))


def _get_engine() -> Engine:
    global _engine, _engine_key
    url = _database_url()
    if url is None:
        raise RuntimeError("Database is not configured.")
    key = str(url)
    if _engine is not None and _engine_key == key:
        return _engine
    with _engine_lock:
        if _engine is not None and _engine_key == key:
            return _engine
        if _engine is not None:
            _engine.dispose()
        options: dict[str, Any] = {"pool_pre_ping": True}
        if key.startswith("sqlite"):
            options["poolclass"] = NullPool
            options["connect_args"] = {
                "check_same_thread": False,
                "timeout": config.DB_CONNECT_TIMEOUT,
            }
        else:
            options.update(
                pool_recycle=1800,
                pool_size=5,
                max_overflow=10,
                connect_args={"connect_timeout": config.DB_CONNECT_TIMEOUT},
            )
        _engine = create_engine(url, **options)
        _engine_key = key
        return _engine


def is_configured() -> bool:
    return _database_url() is not None


def database_health() -> dict[str, Any]:
    if not is_configured():
        return {"status": "not_configured", "engine": config.DB_ENGINE}
    try:
        engine = _get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            if connection.scalar(select(func.max(schema_migrations.c.version))) != SCHEMA_VERSION:
                return {"status": "unavailable", "engine": config.DB_ENGINE, "reason": "Schema migration required"}
        return {"status": "available", "engine": engine.dialect.name.replace("mysql", "mariadb")}
    except (SQLAlchemyError, RuntimeError, OSError):
        return {"status": "unavailable", "engine": config.DB_ENGINE}


def migrate() -> dict[str, Any]:
    if not is_configured():
        return {"status": "not_configured", "applied_versions": []}
    try:
        engine = _get_engine()
        metadata.create_all(engine)
        with engine.begin() as connection:
            applied = set(connection.execute(select(schema_migrations.c.version)).scalars())
            newly_applied = []
            if 1 not in applied:
                connection.execute(insert(schema_migrations).values(version=1))
                newly_applied.append(1)
            if 2 not in applied:
                existing_columns = {column["name"] for column in inspect(engine).get_columns("Annotations")}
                additions = {
                    "annotation_round": "VARCHAR(40) NOT NULL DEFAULT 'reconciliation'",
                    "is_independent": "BOOLEAN NOT NULL DEFAULT 0",
                    "evidence_sufficient": "BOOLEAN NULL",
                }
                for column_name, definition in additions.items():
                    if column_name not in existing_columns:
                        connection.execute(text(f"ALTER TABLE `Annotations` ADD COLUMN `{column_name}` {definition}"))
                connection.execute(insert(schema_migrations).values(version=2))
                newly_applied.append(2)
            if 3 not in applied:
                existing_columns = {
                    column["name"] for column in inspect(engine).get_columns("CandidateSamples")
                }
                additions = {
                    "topic_confidence": "FLOAT NULL",
                    "topic_review_status": "VARCHAR(40) NOT NULL DEFAULT 'auto_suggested'",
                }
                for column_name, definition in additions.items():
                    if column_name not in existing_columns:
                        connection.execute(
                            text(f"ALTER TABLE `CandidateSamples` ADD COLUMN `{column_name}` {definition}")
                        )
                connection.execute(insert(schema_migrations).values(version=3))
                newly_applied.append(3)
            if 4 not in applied:
                existing_columns = {
                    column["name"] for column in inspect(engine).get_columns("TrainingRuns")
                }
                additions = {
                    "progress_percent": "INTEGER NOT NULL DEFAULT 0",
                    "progress_stage": "VARCHAR(120) NOT NULL DEFAULT 'Queued'",
                }
                for column_name, definition in additions.items():
                    if column_name not in existing_columns:
                        connection.execute(
                            text(f"ALTER TABLE `TrainingRuns` ADD COLUMN `{column_name}` {definition}")
                        )
                connection.execute(insert(schema_migrations).values(version=4))
                newly_applied.append(4)
            if 5 not in applied:
                connection.execute(insert(schema_migrations).values(version=5))
                newly_applied.append(5)
        return {"status": "available", "applied_versions": newly_applied}
    except (SQLAlchemyError, RuntimeError, OSError):
        return {"status": "unavailable", "applied_versions": []}


def hash_password(password: str, *, iterations: int = 260_000) -> str:
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
    except (AttributeError, TypeError, ValueError):
        return False


def ensure_bootstrap_admin() -> bool:
    username = config.ADMIN_BOOTSTRAP_USERNAME
    password = config.ADMIN_BOOTSTRAP_PASSWORD
    if not username or not password:
        return False
    with _get_engine().begin() as connection:
        existing = connection.execute(
            select(admin_users.c.admin_user_id).where(admin_users.c.username == username)
        ).first()
        if existing:
            return False
        connection.execute(
            insert(admin_users).values(
                username=username, password_hash=hash_password(password), role="admin"
            )
        )
    return True


def ensure_bootstrap_viewer() -> bool:
    username = config.VIEWER_BOOTSTRAP_USERNAME
    password = config.VIEWER_BOOTSTRAP_PASSWORD
    if not username or not password:
        return False
    with _get_engine().begin() as connection:
        existing = connection.execute(
            select(admin_users.c.admin_user_id).where(admin_users.c.username == username)
        ).first()
        if existing:
            return False
        connection.execute(
            insert(admin_users).values(
                username=username, password_hash=hash_password(password), role="viewer"
            )
        )
    return True


def verify_admin(username: str, password: str) -> dict[str, Any] | None:
    with _get_engine().begin() as connection:
        row = connection.execute(
            select(
                admin_users.c.admin_user_id,
                admin_users.c.username,
                admin_users.c.password_hash,
                admin_users.c.role,
            ).where(admin_users.c.username == username, admin_users.c.is_active.is_(True))
        ).mappings().first()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        connection.execute(
            update(admin_users)
            .where(admin_users.c.admin_user_id == row["admin_user_id"])
            .values(last_login_at=func.now())
        )
        return {"id": row["admin_user_id"], "username": row["username"], "role": row["role"]}


def create_candidate(
    *,
    text: str,
    page_url: str | None,
    page_title: str | None,
    source_type: str = "browser-extension",
    proposed_label: str,
    topic: str | None = None,
    topic_confidence: float | None = None,
) -> int:
    if proposed_label not in {"Misleading", "Non-Misleading"}:
        raise ValueError("Candidate label must be Misleading or Non-Misleading.")
    with _get_engine().begin() as connection:
        result = connection.execute(
            insert(candidate_samples).values(
                text_content=text,
                page_url=page_url,
                page_title=page_title,
                source_type=source_type,
                proposed_label=proposed_label,
                topic=topic,
                topic_confidence=topic_confidence,
                topic_review_status="auto_suggested",
            )
        )
        return int(result.inserted_primary_key[0])


def _candidate_query(*, topic: str | None = None, validation_status: str | None = None,
                     evidence_status: str | None = None):
    evidence_count = (
        select(func.count())
        .select_from(evidence_records)
        .where(evidence_records.c.candidate_sample_id == candidate_samples.c.candidate_sample_id)
        .correlate(candidate_samples)
        .scalar_subquery()
    )
    matched_count = (
        select(func.count())
        .select_from(evidence_records)
        .where(
            evidence_records.c.candidate_sample_id == candidate_samples.c.candidate_sample_id,
            evidence_records.c.claim_match_status == "matched",
        )
        .correlate(candidate_samples)
        .scalar_subquery()
    )
    statement = select(
        candidate_samples,
        evidence_count.label("evidence_count"),
        matched_count.label("matched_evidence_count"),
    )
    if topic:
        statement = statement.where(candidate_samples.c.topic == topic)
    if validation_status:
        statement = statement.where(candidate_samples.c.validation_status == validation_status)
    if evidence_status == "missing":
        statement = statement.where(evidence_count == 0)
    elif evidence_status == "unverified":
        statement = statement.where(evidence_count > 0, matched_count == 0)
    elif evidence_status == "verified":
        statement = statement.where(matched_count > 0)
    return statement


def _with_evidence_status(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("matched_evidence_count", 0):
        row["evidence_status"] = "verified"
    elif row.get("evidence_count", 0):
        row["evidence_status"] = "unverified"
    else:
        row["evidence_status"] = "missing"
    return _serialize_dates(row)


def list_candidates(
    limit: int = 100,
    *,
    topic: str | None = None,
    validation_status: str | None = None,
    evidence_status: str | None = None,
) -> list[dict[str, Any]]:
    with _get_engine().connect() as connection:
        rows = connection.execute(
            _candidate_query(
                topic=topic,
                validation_status=validation_status,
                evidence_status=evidence_status,
            )
            .order_by(candidate_samples.c.submitted_at.desc(), candidate_samples.c.candidate_sample_id.desc())
            .limit(limit)
        ).mappings().all()
    return [_with_evidence_status(dict(row)) for row in rows]


def get_candidate(candidate_id: int) -> dict[str, Any] | None:
    with _get_engine().connect() as connection:
        row = connection.execute(
            select(candidate_samples).where(
                candidate_samples.c.candidate_sample_id == candidate_id
            )
        ).mappings().first()
    return _serialize_dates(dict(row)) if row else None


def candidate_topic_summary() -> dict[str, Any]:
    """Return collection counts for every paper-defined topic, including zeroes."""

    with _get_engine().connect() as connection:
        candidates = connection.execute(
            select(
                candidate_samples.c.candidate_sample_id,
                candidate_samples.c.topic,
                candidate_samples.c.validation_status,
                candidate_samples.c.proposed_label,
            )
        ).mappings().all()
        evidence_candidate_ids = set(
            connection.execute(select(evidence_records.c.candidate_sample_id).distinct()).scalars()
        )
        matched_candidate_ids = set(
            connection.execute(
                select(evidence_records.c.candidate_sample_id)
                .where(evidence_records.c.claim_match_status == "matched")
                .distinct()
            ).scalars()
        )

    topics = {
        topic: {"topic": topic, "total": 0, "misleading": 0, "non_misleading": 0,
                "pending": 0, "approved": 0,
                "missing_evidence": 0, "verified_evidence": 0}
        for topic in config.TOPIC_CATEGORIES
    }
    for row in candidates:
        topic = row["topic"] if row["topic"] in topics else "Other and General"
        bucket = topics[topic]
        bucket["total"] += 1
        if row["proposed_label"] == "Misleading":
            bucket["misleading"] += 1
        elif row["proposed_label"] == "Non-Misleading":
            bucket["non_misleading"] += 1
        if row["validation_status"] == "approved":
            bucket["approved"] += 1
        elif row["validation_status"] in {"pending", "needs_revision"}:
            bucket["pending"] += 1
        candidate_id = row["candidate_sample_id"]
        if candidate_id in matched_candidate_ids:
            bucket["verified_evidence"] += 1
        elif candidate_id not in evidence_candidate_ids:
            bucket["missing_evidence"] += 1

    rows = list(topics.values())
    return {
        "topics": rows,
        "totals": {
            "candidates": len(candidates),
            "approved": sum(row["approved"] for row in rows),
            "pending": sum(row["pending"] for row in rows),
            "misleading": sum(row["misleading"] for row in rows),
            "non_misleading": sum(row["non_misleading"] for row in rows),
            "missing_evidence": sum(row["missing_evidence"] for row in rows),
            "verified_evidence": sum(row["verified_evidence"] for row in rows),
        },
    }


def export_candidates(
    *,
    topic: str | None = None,
    validation_status: str | None = None,
    evidence_status: str | None = None,
) -> list[dict[str, Any]]:
    with _get_engine().connect() as connection:
        candidate_rows = connection.execute(
            _candidate_query(
                topic=topic,
                validation_status=validation_status,
                evidence_status=evidence_status,
            ).order_by(candidate_samples.c.candidate_sample_id)
        ).mappings().all()
        ids = [row["candidate_sample_id"] for row in candidate_rows]
        evidence_rows = connection.execute(
            select(
                evidence_records.c.candidate_sample_id,
                evidence_records.c.source_url,
                evidence_records.c.claim_match_status,
            ).where(evidence_records.c.candidate_sample_id.in_(ids))
        ).mappings().all() if ids else []

    urls: dict[int, list[str]] = {}
    for evidence in evidence_rows:
        marker = "verified" if evidence["claim_match_status"] == "matched" else evidence["claim_match_status"]
        urls.setdefault(evidence["candidate_sample_id"], []).append(
            f"{evidence['source_url']} [{marker}]"
        )

    exported = []
    for raw in candidate_rows:
        row = _with_evidence_status(dict(raw))
        exported.append({
            "candidate_sample_id": row["candidate_sample_id"],
            "text": row["text_content"],
            "input_type": row["source_type"],
            "language": row["language"] or "",
            "topic": row["topic"] or "Other and General",
            "topic_confidence": row["topic_confidence"] if row["topic_confidence"] is not None else "",
            "topic_review_status": row["topic_review_status"],
            "proposed_label": row["proposed_label"] or "",
            "validation_status": row["validation_status"],
            "training_status": row["training_status"],
            "evidence_status": row["evidence_status"],
            "evidence_urls": " | ".join(urls.get(row["candidate_sample_id"], [])),
            "source_url": row["page_url"] or "",
            "page_title": row["page_title"] or "",
            "claim_group_id": row["claim_group_id"] or "",
            "submitted_at": row["submitted_at"],
        })
    return exported


def review_candidate(
    candidate_id: int,
    *,
    decision: str,
    proposed_label: str | None,
    notes: str | None,
    reviewer: str,
    language: str | None = None,
    topic: str | None = None,
    claim_group_id: str | None = None,
) -> dict[str, Any]:
    status_map = {"approve": "approved", "revise": "needs_revision", "exclude": "excluded"}
    if decision not in status_map:
        raise ValueError("Decision must be approve, revise, or exclude.")
    with _get_engine().begin() as connection:
        exists = connection.scalar(
            select(candidate_samples.c.candidate_sample_id).where(
                candidate_samples.c.candidate_sample_id == candidate_id
            )
        )
        if not exists:
            raise LookupError("Candidate sample was not found.")
        if decision == "approve":
            matched_evidence = connection.scalar(
                select(func.count()).select_from(evidence_records).where(
                    evidence_records.c.candidate_sample_id == candidate_id,
                    evidence_records.c.claim_match_status == "matched",
                )
            ) or 0
            if not matched_evidence:
                raise ValueError(
                    "Approval requires at least one manually confirmed matching evidence URL."
                )
        connection.execute(
            insert(annotations).values(
                candidate_sample_id=candidate_id,
                reviewer_identifier=reviewer,
                proposed_label=proposed_label,
                decision=decision,
                annotation_round="reconciliation",
                is_independent=False,
                notes=notes,
            )
        )
        values: dict[str, Any] = {
            "validation_status": status_map[decision],
            "training_status": "eligible" if decision == "approve" else "not_training_data",
        }
        if proposed_label is not None:
            values["proposed_label"] = proposed_label
        if language is not None:
            values["language"] = language
        if topic is not None:
            values["topic"] = topic
            values["topic_review_status"] = "verified"
        if claim_group_id is not None:
            values["claim_group_id"] = claim_group_id
        connection.execute(
            update(candidate_samples)
            .where(candidate_samples.c.candidate_sample_id == candidate_id)
            .values(**values)
        )
    return {"candidate_sample_id": candidate_id, "validation_status": status_map[decision]}


def add_independent_annotation(
    candidate_id: int,
    *,
    reviewer: str,
    proposed_label: str,
    annotation_round: str,
    evidence_sufficient: bool,
    notes: str | None,
) -> int:
    with _get_engine().begin() as connection:
        exists = connection.scalar(select(candidate_samples.c.candidate_sample_id).where(candidate_samples.c.candidate_sample_id == candidate_id))
        if not exists:
            raise LookupError("Candidate sample was not found.")
        duplicate = connection.scalar(select(annotations.c.annotation_id).where(
            annotations.c.candidate_sample_id == candidate_id,
            annotations.c.reviewer_identifier == reviewer,
            annotations.c.annotation_round == annotation_round,
            annotations.c.is_independent.is_(True),
        ))
        if duplicate:
            raise ValueError("This reviewer already annotated the candidate in this round.")
        result = connection.execute(insert(annotations).values(
            candidate_sample_id=candidate_id,
            reviewer_identifier=reviewer,
            proposed_label=proposed_label,
            decision="independent_annotation",
            annotation_round=annotation_round,
            is_independent=True,
            evidence_sufficient=evidence_sufficient,
            notes=notes,
        ))
        return int(result.inserted_primary_key[0])


def list_annotations(candidate_id: int) -> list[dict[str, Any]]:
    with _get_engine().connect() as connection:
        rows = connection.execute(select(annotations).where(
            annotations.c.candidate_sample_id == candidate_id
        ).order_by(annotations.c.created_at)).mappings().all()
    return [_serialize_dates(dict(row)) for row in rows]


def add_evidence(
    candidate_id: int,
    *,
    source_url: str,
    publisher: str | None,
    rating: str | None,
    claim_match_status: str,
    notes: str | None,
    reviewer: str,
) -> int:
    with _get_engine().begin() as connection:
        exists = connection.scalar(
            select(candidate_samples.c.candidate_sample_id).where(
                candidate_samples.c.candidate_sample_id == candidate_id
            )
        )
        if not exists:
            raise LookupError("Candidate sample was not found.")
        result = connection.execute(
            insert(evidence_records).values(
                candidate_sample_id=candidate_id,
                source_url=source_url,
                publisher=publisher,
                rating=rating,
                claim_match_status=claim_match_status,
                reviewer_identifier=reviewer,
                notes=notes,
            )
        )
        return int(result.inserted_primary_key[0])


def list_evidence(candidate_id: int) -> list[dict[str, Any]]:
    with _get_engine().connect() as connection:
        rows = connection.execute(
            select(evidence_records)
            .where(evidence_records.c.candidate_sample_id == candidate_id)
            .order_by(evidence_records.c.created_at.desc())
        ).mappings().all()
    return [_serialize_dates(dict(row)) for row in rows]


def create_dataset_version(version_name: str, description: str | None, created_by: str) -> int:
    with _get_engine().begin() as connection:
        result = connection.execute(
            insert(dataset_versions).values(
                version_name=version_name, description=description, created_by=created_by
            )
        )
        return int(result.inserted_primary_key[0])


def add_dataset_item(
    version_id: int,
    *,
    candidate_id: int,
    final_label: str,
    partition_name: str,
    claim_group_id: str,
) -> int:
    if partition_name not in {"train", "validation", "test"}:
        raise ValueError("Partition must be train, validation, or test.")
    with _get_engine().begin() as connection:
        candidate = connection.execute(
            select(candidate_samples.c.validation_status).where(
                candidate_samples.c.candidate_sample_id == candidate_id
            )
        ).scalar_one_or_none()
        if candidate != "approved":
            raise ValueError("Only approved candidates may enter a dataset version.")
        result = connection.execute(
            insert(dataset_items).values(
                dataset_version_id=version_id,
                candidate_sample_id=candidate_id,
                final_label=final_label,
                partition_name=partition_name,
                claim_group_id=claim_group_id,
            )
        )
        return int(result.inserted_primary_key[0])


def _partition_for_claim_group(claim_group_id: str) -> str:
    bucket = int(hashlib.sha256(claim_group_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


def bulk_add_approved_candidates(version_id: int) -> dict[str, Any]:
    """Add every eligible approved candidate using claim-group-safe deterministic splits."""

    with _get_engine().begin() as connection:
        status = connection.scalar(
            select(dataset_versions.c.status).where(
                dataset_versions.c.dataset_version_id == version_id
            )
        )
        if status != "draft":
            raise ValueError("Candidates may only be added to a draft dataset version.")
        existing_ids = set(connection.execute(
            select(dataset_items.c.candidate_sample_id).where(
                dataset_items.c.dataset_version_id == version_id
            )
        ).scalars())
        rows = connection.execute(
            select(
                candidate_samples.c.candidate_sample_id,
                candidate_samples.c.proposed_label,
                candidate_samples.c.claim_group_id,
            ).where(
                candidate_samples.c.validation_status == "approved",
                candidate_samples.c.proposed_label.in_(("Misleading", "Non-Misleading")),
            )
        ).mappings().all()
        additions = []
        skipped_missing_claim_group = 0
        partition_counts = {"train": 0, "validation": 0, "test": 0}
        for row in rows:
            if row["candidate_sample_id"] in existing_ids:
                continue
            claim_group_id = (row["claim_group_id"] or "").strip()
            if not claim_group_id:
                skipped_missing_claim_group += 1
                continue
            partition = _partition_for_claim_group(claim_group_id)
            partition_counts[partition] += 1
            additions.append({
                "dataset_version_id": version_id,
                "candidate_sample_id": row["candidate_sample_id"],
                "final_label": row["proposed_label"],
                "partition_name": partition,
                "claim_group_id": claim_group_id,
            })
        if additions:
            connection.execute(insert(dataset_items), additions)
    return {
        "added": len(additions),
        "skipped_existing": len(existing_ids),
        "skipped_missing_claim_group": skipped_missing_claim_group,
        "partitions": partition_counts,
    }


def import_validated_dataset(
    version_name: str,
    rows: list[dict[str, Any]],
    *,
    created_by: str,
) -> dict[str, Any]:
    """Create a draft version from already validated, evidence-backed rows."""

    if not rows:
        raise ValueError("The validated dataset contains no rows.")
    with _get_engine().begin() as connection:
        duplicate_name = connection.scalar(
            select(dataset_versions.c.dataset_version_id).where(
                dataset_versions.c.version_name == version_name
            )
        )
        if duplicate_name:
            raise ValueError("A dataset version with this name already exists.")
        version_result = connection.execute(insert(dataset_versions).values(
            version_name=version_name,
            description="Imported validated dataset",
            created_by=created_by,
        ))
        version_id = int(version_result.inserted_primary_key[0])
        partition_counts = {"train": 0, "validation": 0, "test": 0}
        for row in rows:
            partition = row.get("partition_name") or _partition_for_claim_group(row["claim_group_id"])
            candidate_result = connection.execute(insert(candidate_samples).values(
                text_content=row["text"],
                page_url=row.get("source_url"),
                page_title=row.get("page_title"),
                source_type="validated-dataset-import",
                language=row.get("language") or "Taglish",
                topic=row["topic"],
                topic_confidence=1.0,
                topic_review_status="verified",
                claim_group_id=row["claim_group_id"],
                proposed_label=row["label"],
                validation_status="approved",
                training_status="eligible",
            ))
            candidate_id = int(candidate_result.inserted_primary_key[0])
            connection.execute(insert(evidence_records).values(
                candidate_sample_id=candidate_id,
                source_url=row["evidence_url"],
                publisher=row.get("publisher"),
                rating=row.get("rating"),
                claim_match_status="matched",
                reviewer_identifier=created_by,
                notes="Imported as manually validated evidence.",
            ))
            connection.execute(insert(annotations).values(
                candidate_sample_id=candidate_id,
                reviewer_identifier=created_by,
                proposed_label=row["label"],
                decision="approve",
                annotation_round="import",
                is_independent=False,
                evidence_sufficient=True,
                notes="Imported validated dataset row.",
            ))
            connection.execute(insert(dataset_items).values(
                dataset_version_id=version_id,
                candidate_sample_id=candidate_id,
                final_label=row["label"],
                partition_name=partition,
                claim_group_id=row["claim_group_id"],
            ))
            partition_counts[partition] += 1
    return {"dataset_version_id": version_id, "imported": len(rows), "partitions": partition_counts}


def approve_dataset_version(version_id: int) -> None:
    with _get_engine().begin() as connection:
        item_count = connection.scalar(
            select(func.count()).select_from(dataset_items).where(
                dataset_items.c.dataset_version_id == version_id
            )
        ) or 0
        if not item_count:
            raise ValueError("A dataset version must contain approved items before approval.")
        taglish_count = connection.scalar(
            select(func.count())
            .select_from(
                dataset_items.join(
                    candidate_samples,
                    dataset_items.c.candidate_sample_id == candidate_samples.c.candidate_sample_id,
                )
            )
            .where(
                dataset_items.c.dataset_version_id == version_id,
                candidate_samples.c.language == "Taglish",
            )
        ) or 0
        if taglish_count < config.MIN_TAGLISH_SAMPLES:
            raise ValueError(
                f"Dataset version has {taglish_count} Taglish items; {config.MIN_TAGLISH_SAMPLES} are required."
            )
        composition_rows = connection.execute(
            select(
                dataset_items.c.final_label,
                candidate_samples.c.topic,
                candidate_samples.c.language,
                func.count().label("sample_count"),
            )
            .select_from(dataset_items.join(candidate_samples))
            .where(dataset_items.c.dataset_version_id == version_id)
            .group_by(dataset_items.c.final_label, candidate_samples.c.topic, candidate_samples.c.language)
        ).mappings().all()
        if config.ENFORCE_PAPER_DATASET:
            non_taglish = sum(row["sample_count"] for row in composition_rows if row["language"] != "Taglish")
            if non_taglish:
                raise ValueError("Approved model datasets may contain Taglish records only.")
            by_label = {label: 0 for label in ("Misleading", "Non-Misleading")}
            by_topic = {topic: 0 for topic in config.TOPIC_CATEGORIES}
            by_topic_label = {(topic, label): 0 for topic in config.TOPIC_CATEGORIES for label in by_label}
            for row in composition_rows:
                if row["final_label"] in by_label:
                    by_label[row["final_label"]] += row["sample_count"]
                if row["topic"] in by_topic:
                    by_topic[row["topic"]] += row["sample_count"]
                    if row["final_label"] in by_label:
                        by_topic_label[(row["topic"], row["final_label"])] += row["sample_count"]
            failures = []
            failures.extend(f"{label}: {count}/{config.MIN_SAMPLES_PER_CLASS}" for label, count in by_label.items() if count < config.MIN_SAMPLES_PER_CLASS)
            failures.extend(f"{topic}: {count}/{config.MIN_SAMPLES_PER_TOPIC}" for topic, count in by_topic.items() if count < config.MIN_SAMPLES_PER_TOPIC)
            failures.extend(f"{topic} / {label}: {count}/{config.MIN_SAMPLES_PER_TOPIC_CLASS}" for (topic, label), count in by_topic_label.items() if count < config.MIN_SAMPLES_PER_TOPIC_CLASS)
            if failures:
                raise ValueError("Dataset composition does not meet the paper targets: " + "; ".join(failures))
            partition_counts = dict(connection.execute(
                select(dataset_items.c.partition_name, func.count())
                .where(dataset_items.c.dataset_version_id == version_id)
                .group_by(dataset_items.c.partition_name)
            ).all())
            partition_targets = {
                "train": config.MIN_TRAIN_SAMPLES,
                "validation": config.MIN_VALIDATION_SAMPLES,
                "test": config.MIN_TEST_SAMPLES,
            }
            partition_failures = [
                f"{name}: {partition_counts.get(name, 0)}/{target}"
                for name, target in partition_targets.items()
                if partition_counts.get(name, 0) < target
            ]
            if partition_failures:
                raise ValueError("Dataset does not meet the 70/15/15 partition targets: " + "; ".join(partition_failures))
            leaked_groups = connection.execute(
                select(dataset_items.c.claim_group_id)
                .where(dataset_items.c.dataset_version_id == version_id)
                .group_by(dataset_items.c.claim_group_id)
                .having(func.count(func.distinct(dataset_items.c.partition_name)) > 1)
            ).scalars().all()
            if leaked_groups:
                raise ValueError(f"Claim groups cross partitions: {', '.join(leaked_groups[:10])}")
        connection.execute(
            update(dataset_versions)
            .where(dataset_versions.c.dataset_version_id == version_id)
            .values(status="approved", approved_at=func.now())
        )


def list_dataset_versions() -> list[dict[str, Any]]:
    with _get_engine().connect() as connection:
        rows = connection.execute(
            select(dataset_versions).order_by(dataset_versions.c.created_at.desc())
        ).mappings().all()
    return [_serialize_dates(dict(row)) for row in rows]


def dataset_composition(version_id: int) -> list[dict[str, Any]]:
    with _get_engine().connect() as connection:
        rows = connection.execute(
            select(
                candidate_samples.c.language,
                candidate_samples.c.topic,
                dataset_items.c.final_label,
                dataset_items.c.partition_name,
                func.count().label("sample_count"),
            )
            .select_from(dataset_items.join(candidate_samples))
            .where(dataset_items.c.dataset_version_id == version_id)
            .group_by(candidate_samples.c.language, candidate_samples.c.topic, dataset_items.c.final_label, dataset_items.c.partition_name)
        ).mappings().all()
    return [dict(row) for row in rows]


def export_dataset_version(version_id: int) -> list[dict[str, Any]]:
    with _get_engine().connect() as connection:
        status = connection.scalar(
            select(dataset_versions.c.status).where(
                dataset_versions.c.dataset_version_id == version_id
            )
        )
        if status != "approved":
            raise ValueError("Only approved dataset versions may be exported for training.")
        rows = connection.execute(
            select(
                candidate_samples.c.text_content.label("text"),
                dataset_items.c.final_label,
                dataset_items.c.partition_name,
                dataset_items.c.claim_group_id,
            )
            .select_from(
                dataset_items.join(
                    candidate_samples,
                    dataset_items.c.candidate_sample_id == candidate_samples.c.candidate_sample_id,
                )
            )
            .where(dataset_items.c.dataset_version_id == version_id)
        ).mappings().all()
    return [
        {
            "text": row["text"],
            "label": 1 if row["final_label"] == "Misleading" else 0,
            "partition_name": row["partition_name"],
            "claim_group_id": row["claim_group_id"],
        }
        for row in rows
    ]


def queue_training_run(dataset_version_id: int, version_name: str, requested_by: str) -> int:
    with _get_engine().begin() as connection:
        status = connection.scalar(
            select(dataset_versions.c.status).where(
                dataset_versions.c.dataset_version_id == dataset_version_id
            )
        )
        if status != "approved":
            raise ValueError("Retraining requires an approved dataset version.")
        result = connection.execute(
            insert(training_runs).values(
                dataset_version_id=dataset_version_id,
                requested_version_name=version_name,
                requested_by=requested_by,
                progress_percent=0,
                progress_stage="Queued",
            )
        )
        return int(result.inserted_primary_key[0])


def list_training_runs() -> list[dict[str, Any]]:
    with _get_engine().connect() as connection:
        rows = connection.execute(
            select(training_runs).order_by(training_runs.c.requested_at.desc())
        ).mappings().all()
    return [_serialize_dates(dict(row)) for row in rows]


def claim_training_run() -> dict[str, Any] | None:
    with _get_engine().begin() as connection:
        query = (
            select(training_runs)
            .where(training_runs.c.status == "queued")
            .order_by(training_runs.c.requested_at.asc())
            .limit(1)
        )
        if connection.dialect.name != "sqlite":
            query = query.with_for_update(skip_locked=True)
        row = connection.execute(query).mappings().first()
        if not row:
            return None
        connection.execute(
            update(training_runs)
            .where(training_runs.c.training_run_id == row["training_run_id"])
            .values(status="running", progress_percent=5, progress_stage="Preparing dataset", started_at=func.now())
        )
        return dict(row)


def finish_training_run(
    run_id: int, *, status: str, model_version_id: int | None = None, error_message: str | None = None
) -> None:
    with _get_engine().begin() as connection:
        connection.execute(
            update(training_runs)
            .where(training_runs.c.training_run_id == run_id)
            .values(
                status=status,
                progress_percent=100 if status == "completed" else training_runs.c.progress_percent,
                progress_stage="Completed" if status == "completed" else "Failed",
                model_version_id=model_version_id,
                error_message=error_message,
                completed_at=func.now(),
            )
        )


def update_training_progress(run_id: int, progress_percent: int, stage: str) -> None:
    progress = max(0, min(99, int(progress_percent)))
    with _get_engine().begin() as connection:
        connection.execute(
            update(training_runs)
            .where(
                training_runs.c.training_run_id == run_id,
                training_runs.c.status == "running",
            )
            .values(progress_percent=progress, progress_stage=stage[:120])
        )


def register_model_version(
    *, dataset_version_id: int, model_name: str, version_name: str, feature_mode: str,
    metrics: dict[str, Any], artifact_path: str, created_by: str,
) -> int:
    with _get_engine().begin() as connection:
        dataset_status = connection.scalar(
            select(dataset_versions.c.status).where(
                dataset_versions.c.dataset_version_id == dataset_version_id
            )
        )
        if dataset_status != "approved":
            raise ValueError("Models may only be registered against an approved dataset version.")
        result = connection.execute(
            insert(model_versions).values(
                dataset_version_id=dataset_version_id,
                model_name=model_name,
                version_name=version_name,
                feature_mode=feature_mode,
                metrics_json=json.dumps(metrics, separators=(",", ":")),
                artifact_path=artifact_path,
                created_by=created_by,
            )
        )
        return int(result.inserted_primary_key[0])


def review_model_version(model_id: int, decision: str, reviewer: str) -> None:
    if decision not in {"approved", "rejected"}:
        raise ValueError("Model decision must be approved or rejected.")
    with _get_engine().begin() as connection:
        result = connection.execute(
            update(model_versions)
            .where(model_versions.c.model_version_id == model_id, model_versions.c.status == "candidate")
            .values(status=decision, reviewed_by=reviewer, reviewed_at=func.now())
        )
        if result.rowcount != 1:
            raise ValueError("Only a candidate model may be approved or rejected.")


def activate_model_version(model_id: int, reviewer: str) -> dict[str, Any]:
    with _get_engine().begin() as connection:
        model = connection.execute(
            select(model_versions).where(model_versions.c.model_version_id == model_id)
        ).mappings().first()
        if not model or model["status"] != "approved":
            raise ValueError("Only an approved model may be activated.")
        connection.execute(
            update(model_versions)
            .where(model_versions.c.status == "active")
            .values(status="approved", activated_at=None)
        )
        connection.execute(
            update(model_versions)
            .where(model_versions.c.model_version_id == model_id)
            .values(status="active", reviewed_by=reviewer, activated_at=func.now())
        )
        return dict(model)


def get_active_model() -> dict[str, Any] | None:
    with _get_engine().connect() as connection:
        row = connection.execute(
            select(model_versions).where(model_versions.c.status == "active")
        ).mappings().first()
    return dict(row) if row else None


def get_model_version(model_id: int) -> dict[str, Any] | None:
    with _get_engine().connect() as connection:
        row = connection.execute(
            select(model_versions).where(model_versions.c.model_version_id == model_id)
        ).mappings().first()
    return dict(row) if row else None


def list_model_versions() -> list[dict[str, Any]]:
    with _get_engine().connect() as connection:
        rows = connection.execute(
            select(model_versions).order_by(model_versions.c.created_at.desc())
        ).mappings().all()
    values = []
    for row in rows:
        item = _serialize_dates(dict(row))
        item["metrics"] = json.loads(item.pop("metrics_json"))
        values.append(item)
    return values


def log_audit(action: str, description: str, performed_by: str = "system") -> int:
    with _get_engine().begin() as connection:
        result = connection.execute(
            insert(audit_logs).values(
                action=action, description=description, performed_by=performed_by
            )
        )
        return int(result.inserted_primary_key[0])


def list_audits(limit: int = 100) -> list[dict[str, Any]]:
    with _get_engine().connect() as connection:
        rows = connection.execute(
            select(audit_logs)
            .order_by(audit_logs.c.created_at.desc(), audit_logs.c.audit_log_id.desc())
            .limit(limit)
        ).mappings().all()
    return [_serialize_dates(dict(row)) for row in rows]


def sprint_stats() -> dict[str, int]:
    with _get_engine().connect() as connection:
        candidate_total = connection.scalar(select(func.count()).select_from(candidate_samples)) or 0
        pending = connection.scalar(
            select(func.count()).select_from(candidate_samples).where(
                candidate_samples.c.validation_status == "pending"
            )
        ) or 0
        audit_total = connection.scalar(select(func.count()).select_from(audit_logs)) or 0
    return {
        "candidate_samples": int(candidate_total),
        "pending_candidates": int(pending),
        "audit_events": int(audit_total),
    }


def _serialize_dates(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in row.items()
    }


def init_db() -> bool:
    return migrate()["status"] == "available"
