"""KI-Register Pflichtfelder: intended_purpose, training_data_provenance, FRIA, Rollen, PMS."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260407_add_ai_systems_ki_register_fields"
DISPLAY_NAME = "add_ai_systems_ki_register_fields"

_COLUMNS = [
    ("intended_purpose", "TEXT"),
    ("training_data_provenance", "TEXT"),
    ("fria_reference", "VARCHAR(512)"),
    ("provider_name", "VARCHAR(255)"),
    ("deployer_name", "VARCHAR(255)"),
    ("provider_responsibilities", "TEXT"),
    ("deployer_responsibilities", "TEXT"),
    ("pms_status", "VARCHAR(32) NOT NULL DEFAULT 'pending'"),
    ("pms_next_review_date", "DATETIME"),
    ("pms_last_review_date", "DATETIME"),
]


def satisfied(engine: Engine) -> bool:
    """True if all new columns already exist."""
    return all(column_exists(engine, "ai_systems", col) for col, _ in _COLUMNS)


def apply(engine: Engine) -> bool:
    """Add KI-Register columns to ai_systems (additive, no breaking changes)."""
    if not table_exists(engine, "ai_systems"):
        return False
    if satisfied(engine):
        return False
    with engine.begin() as conn:
        for col, dtype in _COLUMNS:
            if not column_exists(engine, "ai_systems", col):
                conn.execute(text(f"ALTER TABLE ai_systems ADD COLUMN {col} {dtype}"))
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
