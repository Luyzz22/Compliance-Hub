"""Store mutable SCIM display names in tenant scope."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260820_scim_tenant_profile"
DISPLAY_NAME = "scim_tenant_profile"


def satisfied(engine: Engine) -> bool:
    return column_exists(engine, "scim_sync_state", "display_name")


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "scim_sync_state") or satisfied(engine):
        return False
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE scim_sync_state ADD COLUMN display_name VARCHAR(255)"))
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
