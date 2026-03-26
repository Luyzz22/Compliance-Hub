"""Add nullable ``tenants.kritis_sector`` (KRITIS Stammdaten, advisory portfolio)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

# Stable id (lexicographic sort = chronological if YYYYMMDD prefix).
MIGRATION_ID = "20260326_add_tenants_kritis_sector"
DISPLAY_NAME = "add_tenants_kritis_sector"


def satisfied(engine: Engine) -> bool:
    """Column already present (e.g. after create_all on a fresh DB)."""
    return column_exists(engine, "tenants", "kritis_sector")


def apply(engine: Engine) -> bool:
    """Run ALTER when the tenants table exists and the column is missing.

    Returns True if DDL was executed this call.
    """
    if not table_exists(engine, "tenants"):
        return False
    if satisfied(engine):
        return False

    stmt = text("ALTER TABLE tenants ADD COLUMN kritis_sector VARCHAR(64)")
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
