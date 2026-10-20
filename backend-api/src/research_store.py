"""Opt-in research records. No default text retention or identifying profiles."""
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, insert, select, update
import config
try:
    from . import database
except ImportError:
    import database

CONSENT_VERSION = "2026-10-19-v1"


def save(prediction, *, text, input_type, sources, retain_text):
    identifier, token = secrets.token_hex(16), secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=config.RESEARCH_RETENTION_DAYS)
    with database._get_engine().begin() as connection:
        connection.execute(insert(database.research_records).values(
            record_id=identifier, withdrawal_hash=hashlib.sha256(token.encode()).hexdigest(),
            consent_version=CONSENT_VERSION, expires_at=expires, input_type=input_type,
            text_content=text if retain_text else None,
            result_json=json.dumps({key: prediction[key] for key in (
                "internal_label", "model_score", "training_run_id", "artifact_sha256", "linguistic_indicators"
            )}), evidence_json=json.dumps(sources) if retain_text else "[]",
        ))
    return {"record_id": identifier, "withdrawal_token": token, "expires_at": expires.isoformat() + "Z", "text_retained": retain_text}


def change(identifier, token, *, usefulness=None, withdraw=False):
    table = database.research_records
    with database._get_engine().begin() as connection:
        row = connection.execute(select(table).where(table.c.record_id == identifier)).mappings().first()
        if not row or not hmac.compare_digest(row["withdrawal_hash"], hashlib.sha256(token.encode()).hexdigest()):
            raise LookupError("Research receipt not found.")
        if withdraw:
            connection.execute(delete(table).where(table.c.record_id == identifier))
        else:
            connection.execute(update(table).where(table.c.record_id == identifier).values(usefulness=usefulness))


def purge_expired():
    with database._get_engine().begin() as connection:
        return connection.execute(delete(database.research_records).where(database.research_records.c.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None))).rowcount


def export_rows():
    # Neither raw text, links, withdrawal capabilities nor timestamps are exported.
    with database._get_engine().connect() as connection:
        rows = connection.execute(select(database.research_records).where(database.research_records.c.expires_at > datetime.now(timezone.utc).replace(tzinfo=None))).mappings()
        return [{"record_id": row["record_id"], "consent_version": row["consent_version"],
                 "input_type": row["input_type"], "usefulness": row["usefulness"],
                 **json.loads(row["result_json"])} for row in rows]
