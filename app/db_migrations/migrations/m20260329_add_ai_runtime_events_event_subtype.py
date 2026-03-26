"""Nullable ``event_subtype`` on ``ai_runtime_events`` (finer grouping for analytics)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260329_add_ai_runtime_events_event_subtype"
DISPLAY_NAME = "add_ai_runtime_events_event_subtype"


def satisfied(engine: Engine) -> bool:
    return column_exists(engine, "ai_runtime_events", "event_subtype")


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "ai_runtime_events"):
        return False
    if satisfied(engine):
        return False
    stmt = text("ALTER TABLE ai_runtime_events ADD COLUMN event_subtype VARCHAR(64)")
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
