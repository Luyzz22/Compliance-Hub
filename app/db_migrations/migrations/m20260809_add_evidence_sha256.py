"""Add ``evidence_files.sha256`` — content hash as the evidence integrity anchor.

Without a digest taken at upload time the platform cannot demonstrate that a stored
document is unchanged, which is the core requirement auditors place on evidence in
ISO 27001 and GoBD reviews.

Existing rows keep ``NULL``: the original bytes may since have changed, so backfilling a
hash from the current file would manufacture a baseline that proves nothing. Verification
reports ``unverifiable`` for those rows instead of a misleading pass.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260809_add_evidence_sha256"
DISPLAY_NAME = "add_evidence_sha256"

_TABLE = "evidence_files"


def satisfied(engine: Engine) -> bool:
    """Column already present (e.g. after ``create_all`` on a fresh DB)."""
    return column_exists(engine, _TABLE, "sha256")


def apply(engine: Engine) -> bool:
    """Add the column and its index. True if DDL ran this call."""
    if not table_exists(engine, _TABLE):
        return False
    if satisfied(engine):
        return False

    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {_TABLE} ADD COLUMN sha256 VARCHAR(64)"))
        conn.execute(
            text(f"CREATE INDEX IF NOT EXISTS ix_evidence_files_sha256 ON {_TABLE} (sha256)")
        )

    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
