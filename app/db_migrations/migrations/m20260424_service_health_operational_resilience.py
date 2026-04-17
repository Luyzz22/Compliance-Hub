"""Operational Resilience: service health snapshots + incidents (NIS2 / ISO monitoring MVP)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260424_service_health_operational_resilience"
DISPLAY_NAME = "service_health_operational_resilience"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "service_health_snapshots")


def apply(engine: Engine) -> bool:
    if table_exists(engine, "service_health_snapshots"):
        return False
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE service_health_snapshots (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                poll_run_id VARCHAR(36) NOT NULL,
                source VARCHAR(64) NOT NULL DEFAULT 'internal_health_poll',
                service_name VARCHAR(64) NOT NULL,
                status VARCHAR(16) NOT NULL,
                checked_at DATETIME NOT NULL,
                raw_payload TEXT NOT NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_service_health_snapshots_tenant_checked "
                "ON service_health_snapshots (tenant_id, checked_at)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_service_health_snapshots_tenant_service "
                "ON service_health_snapshots (tenant_id, service_name, checked_at)"
            )
        )
        conn.execute(
            text("""
            CREATE TABLE service_health_incidents (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                service_name VARCHAR(64) NOT NULL,
                previous_status VARCHAR(16),
                current_status VARCHAR(16) NOT NULL,
                severity VARCHAR(16) NOT NULL,
                incident_state VARCHAR(16) NOT NULL,
                source VARCHAR(64) NOT NULL DEFAULT 'internal_health_poll',
                detected_at DATETIME NOT NULL,
                resolved_at DATETIME,
                updated_at_utc DATETIME NOT NULL,
                triggering_snapshot_id VARCHAR(36),
                title VARCHAR(500) NOT NULL,
                summary TEXT NOT NULL DEFAULT ''
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_service_health_incidents_tenant_state "
                "ON service_health_incidents (tenant_id, incident_state)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_service_health_incidents_tenant_detected "
                "ON service_health_incidents (tenant_id, detected_at)"
            )
        )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
