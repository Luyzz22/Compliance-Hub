"""Rule-based remediation automation, escalations, reminders, and event stream."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260429_remediation_automation_layer"
DISPLAY_NAME = "remediation_automation_layer"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "remediation_automation_runs")


def apply(engine: Engine) -> bool:
    if table_exists(engine, "remediation_automation_runs"):
        return False
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE remediation_automation_runs (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                started_at_utc DATETIME NOT NULL,
                finished_at_utc DATETIME,
                summary_json TEXT,
                escalations_created INTEGER NOT NULL DEFAULT 0,
                reminders_upserted INTEGER NOT NULL DEFAULT 0,
                events_written INTEGER NOT NULL DEFAULT 0,
                generated_actions_count INTEGER NOT NULL DEFAULT 0
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_ra_runs_tenant_started "
                "ON remediation_automation_runs (tenant_id, started_at_utc DESC)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE remediation_escalations (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                action_id VARCHAR(36) NOT NULL,
                run_id VARCHAR(36),
                severity VARCHAR(32) NOT NULL,
                reason_code VARCHAR(64) NOT NULL,
                detail TEXT,
                status VARCHAR(32) NOT NULL DEFAULT 'open',
                created_at_utc DATETIME NOT NULL,
                acknowledged_at_utc DATETIME,
                acknowledged_by VARCHAR(255),
                FOREIGN KEY(action_id) REFERENCES remediation_actions (id) ON DELETE CASCADE,
                FOREIGN KEY(run_id) REFERENCES remediation_automation_runs (id) ON DELETE SET NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_re_tenant_status "
                "ON remediation_escalations (tenant_id, status, severity)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_re_tenant_action "
                "ON remediation_escalations (tenant_id, action_id)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE remediation_reminders (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                action_id VARCHAR(36) NOT NULL,
                run_id VARCHAR(36),
                kind VARCHAR(32) NOT NULL,
                remind_at_utc DATETIME NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'open',
                created_at_utc DATETIME NOT NULL,
                FOREIGN KEY(action_id) REFERENCES remediation_actions (id) ON DELETE CASCADE,
                FOREIGN KEY(run_id) REFERENCES remediation_automation_runs (id) ON DELETE SET NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_rem_tenant_remind "
                "ON remediation_reminders (tenant_id, remind_at_utc, status)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE remediation_action_events (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                action_id VARCHAR(36),
                run_id VARCHAR(36),
                event_type VARCHAR(64) NOT NULL,
                payload_json TEXT,
                created_at_utc DATETIME NOT NULL,
                FOREIGN KEY(action_id) REFERENCES remediation_actions (id) ON DELETE CASCADE,
                FOREIGN KEY(run_id) REFERENCES remediation_automation_runs (id) ON DELETE SET NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_rae_tenant_time "
                "ON remediation_action_events (tenant_id, created_at_utc DESC)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_rae_tenant_type ON remediation_action_events "
                "(tenant_id, event_type)"
            )
        )

    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
