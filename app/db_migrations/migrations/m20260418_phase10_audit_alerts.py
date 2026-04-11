"""Phase 10: NIS2 audit alert table for security-critical event tracking."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260418_phase10_audit_alerts"
DISPLAY_NAME = "phase10_audit_alerts_table"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "audit_alerts")


def apply(engine: Engine) -> bool:
    if table_exists(engine, "audit_alerts"):
        return False
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE audit_alerts (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                audit_log_id INTEGER,
                severity VARCHAR(16) NOT NULL,
                alert_type VARCHAR(128) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                actor VARCHAR(255),
                ip_address VARCHAR(45),
                resolved BOOLEAN NOT NULL DEFAULT 0,
                resolved_by VARCHAR(255),
                resolved_at DATETIME,
                created_at_utc DATETIME NOT NULL
            )
        """)
        )
        conn.execute(
            text("CREATE INDEX idx_audit_alerts_tenant ON audit_alerts (tenant_id)")
        )
        conn.execute(
            text("CREATE INDEX idx_audit_alerts_severity ON audit_alerts (severity)")
        )
        conn.execute(
            text(
                "CREATE INDEX idx_audit_alerts_created ON audit_alerts (created_at_utc)"
            )
        )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
