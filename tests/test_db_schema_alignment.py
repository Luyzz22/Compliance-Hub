"""CI guard: ORM metadata must be reflected in the physical schema (post-migration)."""

from __future__ import annotations

from app.db import engine
from app.db_migrations.schema_alignment import list_orm_columns_missing_in_db


def test_shared_test_db_covers_all_orm_columns() -> None:
    """Session DB is create_all + run_all_db_migrations (see conftest): no drift."""
    missing = list_orm_columns_missing_in_db(engine)
    assert missing == [], (
        "ORM columns missing in DB — add an additive migration under "
        "app/db_migrations/migrations/ (see docs/db-migrations.md). "
        f"Missing: {missing}"
    )
