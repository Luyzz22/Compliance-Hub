"""Add Phase 4 tables: report_exports, xrechnung_exports."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260414_phase4_pdf_xrechnung"
DISPLAY_NAME = "phase4_pdf_xrechnung"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "report_exports") and table_exists(engine, "xrechnung_exports")


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False
    with engine.begin() as conn:
        if not table_exists(engine, "report_exports"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS report_exports (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    report_type VARCHAR(64) NOT NULL,
                    format VARCHAR(32) NOT NULL,
                    file_size_bytes INTEGER NOT NULL DEFAULT 0,
                    checksum VARCHAR(64),
                    requested_by VARCHAR(320),
                    created_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_report_exports_tenant"
                    " ON report_exports (tenant_id)"
                )
            )
        if not table_exists(engine, "xrechnung_exports"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS xrechnung_exports (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    invoice_id VARCHAR(128) NOT NULL,
                    buyer_reference VARCHAR(255) NOT NULL,
                    total_gross FLOAT NOT NULL DEFAULT 0.0,
                    currency VARCHAR(3) NOT NULL DEFAULT 'EUR',
                    validation_errors INTEGER NOT NULL DEFAULT 0,
                    exported_by VARCHAR(320),
                    created_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_xrechnung_exports_tenant"
                    " ON xrechnung_exports (tenant_id)"
                )
            )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
