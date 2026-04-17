"""Unified Control Layer: requirements, controls, framework mappings.

Evidence, reviews, and status history live in sibling tables.
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260425_governance_unified_controls"
DISPLAY_NAME = "governance_unified_controls"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "governance_controls")


def apply(engine: Engine) -> bool:
    if table_exists(engine, "governance_controls"):
        return False
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE governance_requirements (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                requirement_key VARCHAR(128) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                created_at_utc DATETIME NOT NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX uq_governance_requirements_tenant_key "
                "ON governance_requirements (tenant_id, requirement_key)"
            )
        )
        conn.execute(
            text("""
            CREATE TABLE governance_controls (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                requirement_id VARCHAR(36),
                title VARCHAR(500) NOT NULL,
                description TEXT,
                status VARCHAR(32) NOT NULL DEFAULT 'not_started',
                owner VARCHAR(320),
                next_review_at DATETIME,
                framework_tags_json TEXT NOT NULL DEFAULT '[]',
                source_inputs_json TEXT NOT NULL DEFAULT '{}',
                created_at_utc DATETIME NOT NULL,
                updated_at_utc DATETIME NOT NULL,
                created_by VARCHAR(255)
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_governance_controls_tenant_status "
                "ON governance_controls (tenant_id, status)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_governance_controls_tenant_review "
                "ON governance_controls (tenant_id, next_review_at)"
            )
        )
        conn.execute(
            text("""
            CREATE TABLE governance_control_framework_mappings (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                control_id VARCHAR(36) NOT NULL,
                framework VARCHAR(64) NOT NULL,
                clause_ref VARCHAR(256) NOT NULL,
                mapping_note TEXT
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gcfm_control ON governance_control_framework_mappings "
                "(tenant_id, control_id)"
            )
        )
        conn.execute(
            text("""
            CREATE TABLE governance_control_evidence (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                control_id VARCHAR(36) NOT NULL,
                title VARCHAR(500) NOT NULL,
                body_text TEXT,
                source_type VARCHAR(64) NOT NULL DEFAULT 'manual',
                source_ref VARCHAR(256),
                created_at_utc DATETIME NOT NULL,
                created_by VARCHAR(255)
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gce_control ON governance_control_evidence "
                "(tenant_id, control_id)"
            )
        )
        conn.execute(
            text("""
            CREATE TABLE governance_control_reviews (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                control_id VARCHAR(36) NOT NULL,
                due_at DATETIME NOT NULL,
                completed_at DATETIME,
                outcome VARCHAR(32),
                reviewer VARCHAR(320),
                notes TEXT
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gcr_control ON governance_control_reviews (tenant_id, control_id)"
            )
        )
        conn.execute(
            text("""
            CREATE TABLE governance_control_status_history (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                control_id VARCHAR(36) NOT NULL,
                from_status VARCHAR(32),
                to_status VARCHAR(32) NOT NULL,
                changed_at_utc DATETIME NOT NULL,
                changed_by VARCHAR(255),
                note TEXT
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gcsh_control ON governance_control_status_history "
                "(tenant_id, control_id, changed_at_utc)"
            )
        )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
