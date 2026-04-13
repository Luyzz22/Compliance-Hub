"""Phase 14: Add analytics optimisation index on audit_alerts."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import index_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260423_phase14_analytics_indexes"
DISPLAY_NAME = "phase14_analytics_indexes"

_IDX = "ix_audit_alerts_tenant_severity_resolved"


def satisfied(engine: Engine) -> bool:
    if not table_exists(engine, "audit_alerts"):
        return False
    return index_exists(engine, "audit_alerts", _IDX)


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False

    applied = False
    with engine.begin() as conn:
        if table_exists(engine, "audit_alerts") and not index_exists(engine, "audit_alerts", _IDX):
            conn.execute(
                text(f"CREATE INDEX {_IDX} ON audit_alerts (tenant_id, severity, resolved)")
            )
            applied = True

    if applied:
        logger.info("db_migration applied: %s", MIGRATION_ID)
    return applied
