"""Remediation & action tracking (tenant-scoped, linkable entities, dedupe-safe generation)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260428_remediation_actions_layer"
DISPLAY_NAME = "remediation_actions_layer"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "remediation_actions")


def apply(engine: Engine) -> bool:
    if table_exists(engine, "remediation_actions"):
        return False
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE remediation_actions (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                status VARCHAR(32) NOT NULL DEFAULT 'open',
                priority VARCHAR(16) NOT NULL DEFAULT 'medium',
                owner VARCHAR(320),
                due_at_utc DATETIME,
                category VARCHAR(32) NOT NULL DEFAULT 'manual',
                rule_key VARCHAR(64),
                dedupe_key VARCHAR(255),
                deferred_note TEXT,
                created_at_utc DATETIME NOT NULL,
                updated_at_utc DATETIME NOT NULL,
                created_by VARCHAR(255)
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_remediation_actions_tenant_status "
                "ON remediation_actions (tenant_id, status)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_remediation_actions_tenant_due "
                "ON remediation_actions (tenant_id, due_at_utc)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_remediation_actions_tenant_category "
                "ON remediation_actions (tenant_id, category)"
            )
        )
        conn.execute(text("CREATE INDEX ix_remediation_actions_rule_key ON remediation_actions (rule_key)"))
        conn.execute(
            text(
                "CREATE UNIQUE INDEX uq_remediation_actions_tenant_dedupe "
                "ON remediation_actions (tenant_id, dedupe_key)"
                " WHERE dedupe_key IS NOT NULL"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE remediation_action_links (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                action_id VARCHAR(36) NOT NULL,
                entity_type VARCHAR(64) NOT NULL,
                entity_id VARCHAR(255) NOT NULL,
                FOREIGN KEY(action_id) REFERENCES remediation_actions (id) ON DELETE CASCADE
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_ral_tenant_action ON remediation_action_links "
                "(tenant_id, action_id)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_ral_tenant_entity ON remediation_action_links "
                "(tenant_id, entity_type, entity_id)"
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX uq_ral_tenant_action_entity ON remediation_action_links "
                "(tenant_id, action_id, entity_type, entity_id)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE remediation_comments (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                action_id VARCHAR(36) NOT NULL,
                body TEXT NOT NULL,
                created_by VARCHAR(255),
                created_at_utc DATETIME NOT NULL,
                FOREIGN KEY(action_id) REFERENCES remediation_actions (id) ON DELETE CASCADE
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_rc_tenant_action ON remediation_comments (tenant_id, action_id)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE remediation_status_history (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                action_id VARCHAR(36) NOT NULL,
                from_status VARCHAR(32),
                to_status VARCHAR(32) NOT NULL,
                changed_at_utc DATETIME NOT NULL,
                changed_by VARCHAR(255),
                note TEXT,
                FOREIGN KEY(action_id) REFERENCES remediation_actions (id) ON DELETE CASCADE
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_rsh_tenant_action_time ON remediation_status_history "
                "(tenant_id, action_id, changed_at_utc)"
            )
        )

    logger.info("Applied migration %s (%s)", MIGRATION_ID, DISPLAY_NAME)
    return True
