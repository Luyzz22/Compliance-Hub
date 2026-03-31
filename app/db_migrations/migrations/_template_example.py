"""Migration template — **not executed** (filename starts with ``_``, skipped by discovery).

Copy to ``mYYYYMMDD_short_description.py``, set ``MIGRATION_ID`` to the same date prefix
(e.g. ``20260327_add_foo``) so sort order stays chronological.

See ``MIGRATION_TEMPLATE`` below and ``docs/db-migrations.md``.
"""

# Copy-paste body when creating ``mYYYYMMDD_*.py`` (replace placeholders; additive DDL only).
MIGRATION_TEMPLATE = '''
"""One-line description."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

# Use YYYYMMDD_snake_case (no hyphens) so lexicographic sort matches time order.
MIGRATION_ID = "20260327_add_example_column"
DISPLAY_NAME = "add_example_column"


def satisfied(engine: Engine) -> bool:
    """True if the DB already matches the post-migration shape (e.g. after create_all)."""
    return column_exists(engine, "your_table", "your_column")


def apply(engine: Engine) -> bool:
    """True only if this call ran DDL. False if table missing or column already there."""
    if not table_exists(engine, "your_table"):
        return False
    if satisfied(engine):
        return False
    stmt = text("ALTER TABLE your_table ADD COLUMN your_column VARCHAR(255)")
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
'''

__all__ = ["MIGRATION_TEMPLATE"]
