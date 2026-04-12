"""Trust Center & Assurance Portal tables for enterprise evidence management."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260419_trust_center_assurance_portal"
DISPLAY_NAME = "trust_center_assurance_portal_tables"


def satisfied(engine: Engine) -> bool:
    return (
        table_exists(engine, "trust_center_assets")
        and table_exists(engine, "evidence_bundles")
        and table_exists(engine, "trust_center_access_logs")
    )


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False

    with engine.begin() as conn:
        if not table_exists(engine, "trust_center_assets"):
            conn.execute(
                text("""
                CREATE TABLE trust_center_assets (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    description TEXT,
                    asset_type VARCHAR(64) NOT NULL,
                    sensitivity VARCHAR(32) NOT NULL DEFAULT 'customer',
                    framework_refs JSON NOT NULL,
                    file_name VARCHAR(500),
                    published BOOLEAN NOT NULL DEFAULT 0,
                    valid_from DATETIME,
                    valid_until DATETIME,
                    review_date DATETIME,
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_trust_center_assets_tenant ON trust_center_assets (tenant_id)"
                )
            )

        if not table_exists(engine, "evidence_bundles"):
            conn.execute(
                text("""
                CREATE TABLE evidence_bundles (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    bundle_type VARCHAR(64) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    description TEXT,
                    artefact_ids JSON NOT NULL,
                    metadata_payload JSON NOT NULL,
                    sensitivity VARCHAR(32) NOT NULL DEFAULT 'auditor',
                    created_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_evidence_bundles_tenant ON evidence_bundles (tenant_id)"
                )
            )

        if not table_exists(engine, "trust_center_access_logs"):
            conn.execute(
                text("""
                CREATE TABLE trust_center_access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id VARCHAR(255) NOT NULL,
                    actor VARCHAR(255),
                    role VARCHAR(64),
                    action VARCHAR(64) NOT NULL,
                    resource_type VARCHAR(64) NOT NULL,
                    resource_id VARCHAR(36),
                    ip_address VARCHAR(45),
                    created_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX idx_trust_center_access_logs_tenant ON trust_center_access_logs (tenant_id)"
                )
            )

    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
