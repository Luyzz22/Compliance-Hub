"""Add identity_providers, external_identities, scim_sync_state, access_reviews tables."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260411_enterprise_iam_tables"
DISPLAY_NAME = "enterprise_iam_tables"


def satisfied(engine: Engine) -> bool:
    return (
        table_exists(engine, "identity_providers")
        and table_exists(engine, "external_identities")
        and table_exists(engine, "scim_sync_state")
        and table_exists(engine, "access_reviews")
    )


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False
    with engine.begin() as conn:
        if not table_exists(engine, "identity_providers"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS identity_providers (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    slug VARCHAR(128) NOT NULL,
                    display_name VARCHAR(255) NOT NULL,
                    protocol VARCHAR(16) NOT NULL,
                    issuer_url VARCHAR(1024),
                    metadata_url VARCHAR(1024),
                    client_id VARCHAR(255),
                    attribute_mapping TEXT,
                    default_role VARCHAR(64) NOT NULL DEFAULT 'viewer',
                    enabled BOOLEAN NOT NULL DEFAULT 1,
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL,
                    UNIQUE(tenant_id, slug)
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_identity_providers_tenant"
                    " ON identity_providers (tenant_id)"
                )
            )
        if not table_exists(engine, "external_identities"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS external_identities (
                    id VARCHAR(36) PRIMARY KEY,
                    provider_id VARCHAR(36) NOT NULL
                        REFERENCES identity_providers(id) ON DELETE CASCADE,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    external_subject VARCHAR(512) NOT NULL,
                    external_email VARCHAR(320),
                    external_attributes TEXT,
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL,
                    UNIQUE(provider_id, external_subject)
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_external_identities_provider"
                    " ON external_identities (provider_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_external_identities_user"
                    " ON external_identities (user_id)"
                )
            )
        if not table_exists(engine, "scim_sync_state"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS scim_sync_state (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    scim_external_id VARCHAR(512),
                    provision_status VARCHAR(32) NOT NULL DEFAULT 'active',
                    last_sync_at DATETIME,
                    sync_source VARCHAR(128),
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL,
                    UNIQUE(tenant_id, user_id)
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_scim_sync_state_tenant"
                    " ON scim_sync_state (tenant_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_scim_sync_state_user"
                    " ON scim_sync_state (user_id)"
                )
            )
        if not table_exists(engine, "access_reviews"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS access_reviews (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    target_user_id VARCHAR(36) NOT NULL
                        REFERENCES users(id) ON DELETE CASCADE,
                    target_role VARCHAR(64) NOT NULL,
                    reviewer_user_id VARCHAR(36),
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    decision_note TEXT,
                    deadline_utc DATETIME,
                    decided_at_utc DATETIME,
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_access_reviews_tenant"
                    " ON access_reviews (tenant_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_access_reviews_target_user"
                    " ON access_reviews (target_user_id)"
                )
            )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
