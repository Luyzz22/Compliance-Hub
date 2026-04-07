"""Wave 58: connector sync run metrics, lifecycle fields, retry lineage."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260410_enterprise_connector_sync_run_wave58"
DISPLAY_NAME = "enterprise_connector_sync_run_wave58"


def satisfied(engine: Engine) -> bool:
    if not table_exists(engine, "enterprise_connector_sync_runs"):
        return True
    return column_exists(
        engine, "enterprise_connector_sync_runs", "records_received"
    ) and column_exists(engine, "enterprise_connector_sync_runs", "retry_of_sync_run_id")


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "enterprise_connector_sync_runs"):
        return False
    changed = False
    cols: list[tuple[str, str]] = [
        ("records_received", "INTEGER NOT NULL DEFAULT 0"),
        ("records_normalized", "INTEGER NOT NULL DEFAULT 0"),
        ("records_rejected", "INTEGER NOT NULL DEFAULT 0"),
        ("duration_ms", "INTEGER"),
        ("failure_category", "VARCHAR(64)"),
        ("retry_of_sync_run_id", "VARCHAR(120)"),
    ]
    with engine.begin() as conn:
        for name, ddl in cols:
            if not column_exists(engine, "enterprise_connector_sync_runs", name):
                conn.execute(
                    text(f"ALTER TABLE enterprise_connector_sync_runs ADD COLUMN {name} {ddl}")
                )
                changed = True
    if changed:
        logger.info("db_migration applied: %s", MIGRATION_ID)
    return changed
