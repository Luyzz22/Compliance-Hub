"""Anchor NIS2 deadlines on awareness (Art. 23) instead of record-creation time.

Adds ``nis2_incidents.became_aware_at`` and ``nis2_incidents.deadline_basis``.

Existing rows were created with deadlines derived from the record-creation timestamp.
They are backfilled from ``detected_at`` and flagged ``entry_fallback`` so reports and
auditors can tell an approximated deadline from one that was computed from a real
awareness timestamp. Stored deadlines are deliberately left untouched — silently
recomputing historical regulatory deadlines would rewrite the compliance record.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260809_add_nis2_awareness_anchor"
DISPLAY_NAME = "add_nis2_awareness_anchor"

_TABLE = "nis2_incidents"


def satisfied(engine: Engine) -> bool:
    """Both columns already present (e.g. after ``create_all`` on a fresh DB)."""
    return column_exists(engine, _TABLE, "became_aware_at") and column_exists(
        engine, _TABLE, "deadline_basis"
    )


def apply(engine: Engine) -> bool:
    """Add the missing columns and backfill legacy rows. True if DDL ran this call."""
    if not table_exists(engine, _TABLE):
        return False
    if satisfied(engine):
        return False

    with engine.begin() as conn:
        if not column_exists(engine, _TABLE, "became_aware_at"):
            conn.execute(text(f"ALTER TABLE {_TABLE} ADD COLUMN became_aware_at TIMESTAMP"))
        if not column_exists(engine, _TABLE, "deadline_basis"):
            conn.execute(
                text(
                    f"ALTER TABLE {_TABLE} ADD COLUMN deadline_basis VARCHAR(32) "
                    "NOT NULL DEFAULT 'awareness'"
                )
            )
        conn.execute(
            text(
                f"UPDATE {_TABLE} SET became_aware_at = detected_at, "
                "deadline_basis = 'entry_fallback' WHERE became_aware_at IS NULL"
            )
        )

    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
