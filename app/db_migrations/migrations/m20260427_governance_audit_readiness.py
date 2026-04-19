"""Audit readiness: audit cases, scoped frameworks/controls, optional evidence requirements."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260427_governance_audit_readiness"
DISPLAY_NAME = "governance_audit_readiness"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "governance_audit_cases")


def apply(engine: Engine) -> bool:
    if table_exists(engine, "governance_audit_cases"):
        return False
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE governance_audit_cases (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                created_at_utc DATETIME NOT NULL,
                updated_at_utc DATETIME NOT NULL,
                created_by VARCHAR(255)
            )
            """)
        )
        conn.execute(
            text("CREATE INDEX idx_gac_tenant ON governance_audit_cases (tenant_id, status)")
        )
        conn.execute(
            text("""
            CREATE TABLE governance_audit_case_frameworks (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                audit_case_id VARCHAR(36) NOT NULL,
                framework_tag VARCHAR(64) NOT NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_gacf_case ON governance_audit_case_frameworks "
                "(tenant_id, audit_case_id)"
            )
        )
        conn.execute(
            text("""
            CREATE TABLE governance_audit_case_controls (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                audit_case_id VARCHAR(36) NOT NULL,
                control_id VARCHAR(36) NOT NULL,
                attached_at_utc DATETIME NOT NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX uq_gacc_case_control ON governance_audit_case_controls "
                "(tenant_id, audit_case_id, control_id)"
            )
        )
        conn.execute(
            text("""
            CREATE TABLE governance_evidence_requirements (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                framework_tag VARCHAR(64) NOT NULL,
                evidence_type_key VARCHAR(64) NOT NULL,
                label VARCHAR(500) NOT NULL,
                priority INTEGER NOT NULL DEFAULT 2
            )
            """)
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX uq_ger_tenant_fw_type ON governance_evidence_requirements "
                "(tenant_id, framework_tag, evidence_type_key)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_ger_tenant_fw ON governance_evidence_requirements "
                "(tenant_id, framework_tag)"
            )
        )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
