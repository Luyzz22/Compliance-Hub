#!/usr/bin/env python3
"""CLI: Standard-KPI-Definitionen in die Datenbank einspielen (idempotent)."""

from __future__ import annotations

import sys
from pathlib import Path

# Repo-Root
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.db import SessionLocal  # noqa: E402
from app.services.ai_kpi_seed import ensure_ai_kpi_definitions_seeded  # noqa: E402


def main() -> None:
    s = SessionLocal()
    try:
        ensure_ai_kpi_definitions_seeded(s)
        print("ai_kpi_definitions: OK (idempotent seed)")
    finally:
        s.close()


if __name__ == "__main__":
    main()
