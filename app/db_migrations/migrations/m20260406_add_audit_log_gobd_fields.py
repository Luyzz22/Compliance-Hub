"""Add GoBD §14 fields (ip_address, user_agent, previous_hash, entry_hash) to audit_logs."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260406_add_audit_log_gobd_fields"
DISPLAY_NAME = "add_audit_log_gobd_fields"

_COLUMNS = [
    ("ip_address", "VARCHAR(45)"),
    ("user_agent", "VARCHAR(512)"),
    ("previous_hash", "VARCHAR(64)"),
    ("entry_hash", "VARCHAR(64)"),
]


def satisfied(engine: Engine) -> bool:
    """True if all four GoBD columns already exist."""
    return all(column_exists(engine, "audit_logs", col) for col, _ in _COLUMNS)


def apply(engine: Engine) -> bool:
    """Add missing GoBD columns. Returns True if DDL was executed."""
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
