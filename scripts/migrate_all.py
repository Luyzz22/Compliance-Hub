#!/usr/bin/env python3
"""Run additive DB migrations (idempotent).

Uses the same database URL as the API: ``COMPLIANCEHUB_DB_URL`` (see ``app.db``).

Examples:

  python scripts/migrate_all.py
  python scripts/migrate_all.py -v
  COMPLIANCEHUB_DB_URL=postgresql+psycopg://... python scripts/migrate_all.py

For local SQLite (default), this matches ``./test_compliancehub.db`` unless overridden.
"""

from __future__ import annotations

import argparse
import logging
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
        help="Only print output when something changed (DDL or ledger).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging (migration discovery and deferred steps).",
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    url = get_database_url()
    engine = create_db_engine(url)
    try:
        summary = run_all_db_migrations(engine)
    finally:
        engine.dispose()

    if not summary.ledger_available:
        print(
            "Ledger unavailable (no schema_migrations table): read-only / restricted role — "
            "no DDL from this run; use a privileged role to run migrations if needed.",
        )
    if summary.ledgerless_unsatisfied:
        print(
            "WARNING: migrations not satisfied (DBA may need to apply DDL):",
            ", ".join(summary.ledgerless_unsatisfied),
        )
    if summary.applied_ddl or summary.ledger_backfilled or summary.skipped_ledger:
        if summary.applied_ddl:
            print("DDL applied:", ", ".join(summary.applied_ddl))
        if summary.ledger_backfilled:
            print(
                "Ledger backfilled (schema already matched):",
                ", ".join(summary.ledger_backfilled),
            )
        if summary.skipped_ledger:
            print("Skipped (already in schema_migrations):", ", ".join(summary.skipped_ledger))
    elif not args.quiet and summary.ledger_available and not summary.ledgerless_unsatisfied:
        print("No pending migrations (database URL:", url, ")")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
