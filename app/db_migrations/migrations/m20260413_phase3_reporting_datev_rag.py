"""Add Phase 3 tables: compliance_scores, gap_reports, datev_export_logs, norm_embeddings."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260413_phase3_reporting_datev_rag"
DISPLAY_NAME = "phase3_reporting_datev_rag"


def satisfied(engine: Engine) -> bool:
    return (
        table_exists(engine, "compliance_scores")
        and table_exists(engine, "gap_reports")
        and table_exists(engine, "datev_export_logs")
        and table_exists(engine, "norm_embeddings")
    )


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False
    with engine.begin() as conn:
        if not table_exists(engine, "compliance_scores"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS compliance_scores (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    score_type VARCHAR(64) NOT NULL,
                    norm VARCHAR(128),
                    score_value FLOAT NOT NULL,
                    weight FLOAT NOT NULL DEFAULT 1.0,
                    details_json TEXT,
                    period VARCHAR(32) NOT NULL,
                    created_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_compliance_scores_tenant"
                    " ON compliance_scores (tenant_id)"
                )
            )
        if not table_exists(engine, "gap_reports"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS gap_reports (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    norm_scope VARCHAR(255) NOT NULL,
                    gaps_json TEXT,
                    summary TEXT,
                    llm_model VARCHAR(128),
                    llm_trace_id VARCHAR(255),
                    requested_by VARCHAR(320),
                    created_at_utc DATETIME NOT NULL,
                    completed_at_utc DATETIME
                )
            """)
            )
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_gap_reports_tenant ON gap_reports (tenant_id)")
            )
        if not table_exists(engine, "datev_export_logs"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS datev_export_logs (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    export_type VARCHAR(64) NOT NULL,
                    period_from VARCHAR(10) NOT NULL,
                    period_to VARCHAR(10) NOT NULL,
                    record_count INTEGER NOT NULL DEFAULT 0,
                    checksum VARCHAR(64),
                    exported_by VARCHAR(320),
                    step_up_verified BOOLEAN NOT NULL DEFAULT 0,
                    created_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_datev_export_logs_tenant"
                    " ON datev_export_logs (tenant_id)"
                )
            )
        if not table_exists(engine, "norm_embeddings"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS norm_embeddings (
                    id VARCHAR(36) PRIMARY KEY,
                    norm VARCHAR(128) NOT NULL,
                    article_ref VARCHAR(128) NOT NULL,
                    chunk_index INTEGER NOT NULL DEFAULT 0,
                    text_content TEXT NOT NULL,
                    embedding_json TEXT,
                    embedding_model VARCHAR(128),
                    valid_from VARCHAR(10),
                    metadata_json TEXT,
                    created_at_utc DATETIME NOT NULL,
                    UNIQUE(norm, article_ref, chunk_index)
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_norm_embeddings_norm ON norm_embeddings (norm)"
                )
            )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
