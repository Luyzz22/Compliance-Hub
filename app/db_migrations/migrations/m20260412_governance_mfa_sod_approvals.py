"""Add governance tables: mfa, sod, approvals, privileged action events."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260412_governance_mfa_sod_approvals"
DISPLAY_NAME = "governance_mfa_sod_approvals"


def satisfied(engine: Engine) -> bool:
    return (
        table_exists(engine, "mfa_factors")
        and table_exists(engine, "mfa_backup_codes")
        and table_exists(engine, "sod_policies")
        and table_exists(engine, "approval_requests")
        and table_exists(engine, "privileged_action_events")
    )


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False
    with engine.begin() as conn:
        if not table_exists(engine, "mfa_factors"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS mfa_factors (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    factor_type VARCHAR(32) NOT NULL DEFAULT 'totp',
                    secret_encrypted VARCHAR(512) NOT NULL,
                    verified BOOLEAN NOT NULL DEFAULT 0,
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_mfa_factors_user ON mfa_factors (user_id)")
            )
        if not table_exists(engine, "mfa_backup_codes"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS mfa_backup_codes (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    code_hash VARCHAR(255) NOT NULL,
                    used BOOLEAN NOT NULL DEFAULT 0,
                    created_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_mfa_backup_codes_user"
                    " ON mfa_backup_codes (user_id)"
                )
            )
        if not table_exists(engine, "sod_policies"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS sod_policies (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    role_a VARCHAR(64) NOT NULL,
                    role_b VARCHAR(64) NOT NULL,
                    description TEXT,
                    severity VARCHAR(32) NOT NULL DEFAULT 'block',
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL,
                    UNIQUE(tenant_id, role_a, role_b)
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_sod_policies_tenant ON sod_policies (tenant_id)"
                )
            )
        if not table_exists(engine, "approval_requests"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS approval_requests (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    request_type VARCHAR(64) NOT NULL,
                    requester_user_id VARCHAR(36) NOT NULL,
                    target_user_id VARCHAR(36),
                    payload TEXT,
                    status VARCHAR(32) NOT NULL DEFAULT 'requested',
                    approver_user_id VARCHAR(36),
                    decision_note TEXT,
                    decided_at_utc DATETIME,
                    expires_at_utc DATETIME,
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_approval_requests_tenant"
                    " ON approval_requests (tenant_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_approval_requests_status"
                    " ON approval_requests (status)"
                )
            )
        if not table_exists(engine, "privileged_action_events"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS privileged_action_events (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    actor_user_id VARCHAR(36) NOT NULL,
                    action VARCHAR(128) NOT NULL,
                    target_type VARCHAR(64),
                    target_id VARCHAR(36),
                    detail TEXT,
                    step_up_verified BOOLEAN NOT NULL DEFAULT 0,
                    approval_id VARCHAR(36),
                    created_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_priv_action_events_tenant"
                    " ON privileged_action_events (tenant_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_priv_action_events_actor"
                    " ON privileged_action_events (actor_user_id)"
                )
            )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
