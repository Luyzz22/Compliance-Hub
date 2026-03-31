#!/usr/bin/env python3
"""Historical entry point: adds ``tenants.kritis_sector`` if missing.

New deployments should prefer ``scripts/migrate_all.py``, which includes this step
and future additive migrations.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.db import create_db_engine  # noqa: E402
from app.db_migrations import migrate_add_tenants_kritis_sector  # noqa: E402


def main() -> int:
    engine = create_db_engine()
    try:
        if migrate_add_tenants_kritis_sector(engine):
            print("Applied: 20260326_add_tenants_kritis_sector")
        else:
            print("No change (column already present or tenants table missing).")
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
