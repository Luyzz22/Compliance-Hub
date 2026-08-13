#!/usr/bin/env python3
"""Read-only production database schema gate for a candidate backend image."""

from __future__ import annotations

import json

from app.db import engine
from app.db_migrations import list_unsatisfied_db_migrations
from app.db_migrations.schema_alignment import list_orm_columns_missing_in_db


def schema_gate_payload() -> dict[str, object]:
    missing_schema = list_orm_columns_missing_in_db(engine)
    unsatisfied_migrations = list_unsatisfied_db_migrations(engine)
    return {
        "passed": not missing_schema and not unsatisfied_migrations,
        "missing_schema": missing_schema,
        "unsatisfied_migrations": unsatisfied_migrations,
    }


def main() -> int:
    try:
        payload = schema_gate_payload()
    except Exception as exc:
        payload = {
            "passed": False,
            "errors": [f"database schema verification failed ({type(exc).__name__})"],
        }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["passed"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
