"""Compare live DB schema to SQLAlchemy ORM metadata (guardrail for missing migrations)."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from app.models_db import Base


def list_orm_columns_missing_in_db(
    engine: Engine,
    *,
    require_all_tables: bool = True,
) -> list[str]:
    """Return ``table.column`` keys present on ORM models but absent from the physical schema.

    With ``require_all_tables=True`` (default), every ORM table must exist — used in CI on a
    full ``create_all`` database. With ``require_all_tables=False``, only tables that already
    exist in the DB are checked (partial / legacy upgrade smoke tests).
    """
    missing: list[str] = []
    insp = inspect(engine)
    for table in Base.metadata.sorted_tables:
        tname = table.name
        if not insp.has_table(tname):
            if require_all_tables:
                missing.append(f"{tname}.* (table missing)")
            continue
        db_cols = {c["name"] for c in insp.get_columns(tname)}
        for col in table.columns:
            if col.name not in db_cols:
                missing.append(f"{tname}.{col.name}")
    return missing
