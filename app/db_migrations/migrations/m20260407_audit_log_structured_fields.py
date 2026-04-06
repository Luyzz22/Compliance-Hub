"""Add structured governance fields to audit_logs (actor_role, outcome, correlation, metadata)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260407_audit_log_structured_fields"
DISPLAY_NAME = "audit_log_structured_fields"

_COLUMNS = [
    ("actor_role", "VARCHAR(64)"),
    ("outcome", "VARCHAR(32)"),
    ("correlation_id", "VARCHAR(128)"),
    ("metadata_json", "TEXT"),
]


def satisfied(engine: Engine) -> bool:
    return all(column_exists(engine, "audit_logs", col) for col, _ in _COLUMNS)


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "audit_logs"):
        return False
    if satisfied(engine):
        return False
    with engine.begin() as conn:
        for col, col_type in _COLUMNS:
            if not column_exists(engine, "audit_logs", col):
                conn.execute(text(f"ALTER TABLE audit_logs ADD COLUMN {col} {col_type}"))
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
