"""Governance Workflow Orchestration: runs, tasks, events, notification audit (MVP)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260430_governance_workflow_orchestration"
DISPLAY_NAME = "governance_workflow_orchestration"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "governance_workflow_runs")


def apply(engine: Engine) -> bool:
    if table_exists(engine, "governance_workflow_runs"):
        return False
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE governance_workflow_templates (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                code VARCHAR(64) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                default_sla_days INTEGER NOT NULL DEFAULT 5,
                is_system INTEGER NOT NULL DEFAULT 1
            )
            """)
        )
        conn.execute(text("CREATE UNIQUE INDEX uq_gwt_code ON governance_workflow_templates (code)"))

        conn.execute(
            text("""
            CREATE TABLE governance_workflow_runs (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                trigger_mode VARCHAR(32) NOT NULL DEFAULT 'rule_sync',
                status VARCHAR(32) NOT NULL,
                rule_bundle_version VARCHAR(64) NOT NULL,
                summary_json TEXT NOT NULL DEFAULT '{}',
                started_at_utc DATETIME NOT NULL,
                completed_at_utc DATETIME
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gwr_tenant_started "
                "ON governance_workflow_runs (tenant_id, started_at_utc)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE governance_workflow_tasks (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                run_id VARCHAR(36),
                template_code VARCHAR(64),
                title VARCHAR(500) NOT NULL,
                description TEXT,
                status VARCHAR(32) NOT NULL,
                priority VARCHAR(16) NOT NULL DEFAULT 'medium',
                source_type VARCHAR(64) NOT NULL,
                source_id VARCHAR(255) NOT NULL,
                source_ref_json TEXT NOT NULL DEFAULT '{}',
                assignee_user_id VARCHAR(320),
                due_at_utc DATETIME,
                framework_tags_json TEXT NOT NULL DEFAULT '[]',
                dedupe_key VARCHAR(255),
                escalation_level INTEGER NOT NULL DEFAULT 0,
                last_comment TEXT,
                created_at_utc DATETIME NOT NULL,
                updated_at_utc DATETIME NOT NULL,
                created_by VARCHAR(255),
                FOREIGN KEY (run_id) REFERENCES governance_workflow_runs (id) ON DELETE SET NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gwtask_tenant_status_due "
                "ON governance_workflow_tasks (tenant_id, status, due_at_utc)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX uq_gwtask_tenant_dedupe "
                "ON governance_workflow_tasks (tenant_id, dedupe_key)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE governance_workflow_task_history (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                task_id VARCHAR(36) NOT NULL,
                at_utc DATETIME NOT NULL,
                from_status VARCHAR(32),
                to_status VARCHAR(32) NOT NULL,
                actor_id VARCHAR(255) NOT NULL DEFAULT 'system',
                note TEXT,
                payload_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (task_id) REFERENCES governance_workflow_tasks (id) ON DELETE CASCADE
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gwthist_tenant_task "
                "ON governance_workflow_task_history (tenant_id, task_id, at_utc)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE governance_workflow_events (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                at_utc DATETIME NOT NULL,
                event_type VARCHAR(64) NOT NULL,
                severity VARCHAR(16) NOT NULL DEFAULT 'info',
                ref_task_id VARCHAR(36),
                source_type VARCHAR(64) NOT NULL,
                source_id VARCHAR(255) NOT NULL,
                message VARCHAR(2000) NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (ref_task_id) REFERENCES governance_workflow_tasks (id) ON DELETE SET NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gwev_tenant_at "
                "ON governance_workflow_events (tenant_id, at_utc)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE governance_workflow_notifications (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                ref_task_id VARCHAR(36),
                channel VARCHAR(32) NOT NULL DEFAULT 'n8n_webhook',
                status VARCHAR(32) NOT NULL,
                title VARCHAR(500) NOT NULL,
                body_text TEXT NOT NULL DEFAULT '',
                created_at_utc DATETIME NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (ref_task_id) REFERENCES governance_workflow_tasks (id) ON DELETE SET NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gwn_tenant_status "
                "ON governance_workflow_notifications (tenant_id, status, created_at_utc)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE governance_workflow_notification_deliveries (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                notification_id VARCHAR(36) NOT NULL,
                channel VARCHAR(32) NOT NULL,
                result VARCHAR(32) NOT NULL,
                detail TEXT,
                delivered_at_utc DATETIME NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (notification_id) REFERENCES governance_workflow_notifications (id) ON DELETE CASCADE
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gwnd_tenant "
                "ON governance_workflow_notification_deliveries (tenant_id, delivered_at_utc)"
            )
        )

    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
