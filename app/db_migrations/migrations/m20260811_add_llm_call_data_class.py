"""Persist the declared data class with content-free LLM call metadata."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260811_add_llm_call_data_class"
DISPLAY_NAME = "add_llm_call_data_class"


def satisfied(engine: Engine) -> bool:
    return column_exists(engine, "llm_call_metadata", "data_class")


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "llm_call_metadata"):
        return False
    if satisfied(engine):
        return False
    stmt = text(
        "ALTER TABLE llm_call_metadata "
        "ADD COLUMN data_class VARCHAR(32) NOT NULL DEFAULT 'internal'"
    )
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
