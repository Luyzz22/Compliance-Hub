"""Composite index ``(tenant_id, ai_system_id, occurred_at DESC)`` for OAMI / reporting windows.

Ledgerless mode (app role cannot create ``schema_migrations``): ``run_all_db_migrations`` does
not call ``apply()`` — only ``satisfied()`` runs. If this index is missing, the migration id
appears in ``ledgerless_unsatisfied``; create the index with a DDL-capable role
(``python scripts/migrate_all.py``) or DBA tooling.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import index_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260328_add_ai_runtime_events_tenant_system_time_idx"
DISPLAY_NAME = "add_ai_runtime_events_tenant_system_time_idx"

INDEX_NAME = "ix_ai_runtime_events_tenant_system_time"


def satisfied(engine: Engine) -> bool:
    """True once the index exists (including after ``create_all`` on a fresh DB)."""
    return index_exists(engine, "ai_runtime_events", INDEX_NAME)


def apply(engine: Engine) -> bool:
    """Create the index if the table exists and the index is missing (idempotent)."""
    if not table_exists(engine, "ai_runtime_events"):
        return False
    if satisfied(engine):
        return False
    stmt = text(
        f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON ai_runtime_events "
        "(tenant_id, ai_system_id, occurred_at DESC)"
    )
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
