"""Phase 7: Add is_system, status columns to compliance_deadlines; allow nullable tenant_id."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260416_phase7_compliance_calendar_system_deadlines"
DISPLAY_NAME = "phase7_compliance_calendar_system_deadlines"


def satisfied(engine: Engine) -> bool:
    if not table_exists(engine, "compliance_deadlines"):
        return False
    return column_exists(engine, "compliance_deadlines", "is_system") and column_exists(
        engine, "compliance_deadlines", "status"
    )


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "compliance_deadlines"):
        return False
    changed = False
    with engine.begin() as conn:
        if not column_exists(engine, "compliance_deadlines", "is_system"):
            conn.execute(
                text(
                    "ALTER TABLE compliance_deadlines"
                    " ADD COLUMN is_system BOOLEAN NOT NULL DEFAULT 0"
                )
            )
            changed = True
        if not column_exists(engine, "compliance_deadlines", "status"):
            conn.execute(
                text(
                    "ALTER TABLE compliance_deadlines"
                    " ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'open'"
                )
            )
            changed = True
    if changed:
        logger.info("db_migration applied: %s", MIGRATION_ID)
    return changed
