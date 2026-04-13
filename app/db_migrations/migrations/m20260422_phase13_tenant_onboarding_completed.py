"""Phase 13: Add onboarding_completed_at column to tenants table."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260422_phase13_tenant_onboarding_completed"
DISPLAY_NAME = "phase13_tenant_onboarding_completed"


def satisfied(engine: Engine) -> bool:
    return column_exists(engine, "tenants", "onboarding_completed_at")


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False

    applied = False
    with engine.begin() as conn:
        if table_exists(engine, "tenants"):
            if not column_exists(engine, "tenants", "onboarding_completed_at"):
                conn.execute(
                    text("ALTER TABLE tenants ADD COLUMN onboarding_completed_at DATETIME")
                )
                applied = True

    if applied:
        logger.info("db_migration applied: %s", MIGRATION_ID)
    return applied
