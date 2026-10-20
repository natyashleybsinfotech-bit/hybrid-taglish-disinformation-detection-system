"""Add a small set of development-only candidates to the configured database."""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "src"))

from database import create_candidate, log_audit, migrate


SAMPLES = (
    ("BREAKING: May ayuda raw bukas, i-share agad bago matanggal.", "Misleading"),
    ("The local government published its official class suspension advisory.", "Non-Misleading"),
    ("Scientists released a peer-reviewed public-health study this week.", "Non-Misleading"),
    ("Grabe ito! Secret cure daw na ayaw ipaalam ng mga doktor.", "Misleading"),
)


def populate() -> None:
    if migrate()["status"] != "available":
        raise RuntimeError("Database initialization failed. Check the configured SURI database settings.")
    for text, label in SAMPLES:
        candidate_id = create_candidate(
            text=text, page_url=None, page_title="Sample data", proposed_label=label
        )
        log_audit(
            "CANDIDATE_SUBMITTED",
            f"Sample candidate {candidate_id} added by the local population script.",
            "system",
        )
    print(f"Added {len(SAMPLES)} development candidate samples.")


if __name__ == "__main__":
    populate()
