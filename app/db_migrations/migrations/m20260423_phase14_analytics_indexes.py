"""Phase 14: Add analytics optimisation index on audit_alerts."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260423_phase14_analytics_indexes"
DISPLAY_NAME = "phase14_analytics_indexes"


def _index_exists(engine: Engine, table: str, index_name: str) -> bool:
    with engine.connect() as conn:
        dialect = engine.dialect.name
        if dialect == "sqlite":
            rows = conn.execute(
                text(f"PRAGMA index_list('{table}')")
            ).fetchall()
            return any(r[1] == index_name for r in rows)
        rows = conn.execute(
            text(
                "SELECT 1 FROM information_schema.statistics "
                f"WHERE table_name = '{table}' AND index_name = '{index_name}' LIMIT 1"
            )
        ).fetchall()
        return len(rows) > 0


def satisfied(engine: Engine) -> bool:
    if not table_exists(engine, "audit_alerts"):
        return False
    return _index_exists(engine, "audit_alerts", "ix_audit_alerts_tenant_severity_resolved")


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False

    applied = False
    with engine.begin() as conn:
        if table_exists(engine, "audit_alerts"):
            if not _index_exists(
                engine, "audit_alerts", "ix_audit_alerts_tenant_severity_resolved"
            ):
                conn.execute(
                    text(
                        "CREATE INDEX ix_audit_alerts_tenant_severity_resolved "
                        "ON audit_alerts (tenant_id, severity, resolved)"
                    )
                )
                applied = True

    if applied:
        logger.info("db_migration applied: %s", MIGRATION_ID)
    return applied
