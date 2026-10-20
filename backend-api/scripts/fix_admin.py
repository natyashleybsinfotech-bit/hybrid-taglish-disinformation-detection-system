"""Initialize the configured database and bootstrap administrator/viewer accounts."""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "src"))

import database


def fix_admin() -> None:
    migration = database.migrate()
    if migration["status"] != "available":
        raise RuntimeError("Database initialization failed. Check the configured SURI database settings.")
    if not database.config.ADMIN_BOOTSTRAP_USERNAME or not database.config.ADMIN_BOOTSTRAP_PASSWORD:
        raise RuntimeError("Set SURI_ADMIN_USERNAME and SURI_ADMIN_PASSWORD in .env first.")
    created = database.ensure_bootstrap_admin()
    viewer_created = database.ensure_bootstrap_viewer()
    print(f"Database is ready; administrator {'created' if created else 'already exists'}; viewer {'created' if viewer_created else 'already exists or not configured'}.")


if __name__ == "__main__":
    fix_admin()
