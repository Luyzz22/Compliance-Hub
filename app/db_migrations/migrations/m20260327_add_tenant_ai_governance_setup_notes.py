"""Nullable ``setup_notes`` on ``tenant_ai_governance_setup`` (optional DevEx / internal note)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260327_add_tenant_ai_governance_setup_notes"
DISPLAY_NAME = "add_tenant_ai_governance_setup_notes"


def satisfied(engine: Engine) -> bool:
    return column_exists(engine, "tenant_ai_governance_setup", "setup_notes")


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "tenant_ai_governance_setup"):
        return False
    if satisfied(engine):
        return False
    stmt = text("ALTER TABLE tenant_ai_governance_setup ADD COLUMN setup_notes TEXT")
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
