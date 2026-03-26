"""Shared helpers for idempotent DDL (inspect before ALTER)."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def table_exists(engine: Engine, table: str) -> bool:
    return inspect(engine).has_table(table)


def column_exists(engine: Engine, table: str, column: str) -> bool:
    insp = inspect(engine)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))
