#!/usr/bin/env python3
"""Run additive DB migrations (idempotent).

Uses the same database URL as the API: ``COMPLIANCEHUB_DB_URL`` (see ``app.db``).

Examples:

  python scripts/migrate_all.py
  COMPLIANCEHUB_DB_URL=postgresql+psycopg://... python scripts/migrate_all.py

For local SQLite (default), this matches ``./test_compliancehub.db`` unless overridden.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.db import create_db_engine, get_database_url  # noqa: E402
from app.db_migrations import run_all_db_migrations  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ComplianceHub DB migrations.")
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only print output when migrations were applied.",
    )
    args = parser.parse_args()
    url = get_database_url()
    engine = create_db_engine(url)
    try:
        applied = run_all_db_migrations(engine)
    finally:
        engine.dispose()
    if applied:
        print("Applied:", ", ".join(applied))
    elif not args.quiet:
        print("No pending migrations (database URL:", url, ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
