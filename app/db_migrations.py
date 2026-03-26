"""Additive, idempotent schema migrations for existing databases.

`Base.metadata.create_all()` only creates missing tables; it does not ALTER existing
tables when new ORM columns are added. Migrations here close that gap until Alembic
(or similar) is adopted.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _tenants_table_exists(engine: Engine) -> bool:
    return inspect(engine).has_table("tenants")


def _column_exists(engine: Engine, table: str, column: str) -> bool:
    insp = inspect(engine)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def migrate_add_tenants_kritis_sector(engine: Engine) -> bool:
    """Ensure ``tenants.kritis_sector`` exists (nullable VARCHAR(64)).

    Returns True if an ALTER was executed, False if the column was already present
    or the ``tenants`` table does not exist yet.
    """
    if not _tenants_table_exists(engine):
        return False
    if _column_exists(engine, "tenants", "kritis_sector"):
        return False

    stmt = text("ALTER TABLE tenants ADD COLUMN kritis_sector VARCHAR(64)")
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("db_migration applied: add_tenants_kritis_sector")
    return True


def run_all_db_migrations(engine: Engine) -> list[str]:
    """Run all registered migrations in order; each is idempotent.

    Returns human-readable ids of migrations that executed an ALTER this run.
    """
    applied: list[str] = []
    if migrate_add_tenants_kritis_sector(engine):
        applied.append("20260326_add_tenants_kritis_sector")
    return applied
