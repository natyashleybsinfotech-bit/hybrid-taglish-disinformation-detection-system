"""Print the active model bundle metadata and deployment hash."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "src"))

from model_runtime import initialize_model


if __name__ == "__main__":
    health = initialize_model()
    print(json.dumps(health, indent=2))
    raise SystemExit(0 if health["status"] == "ready" else 1)
