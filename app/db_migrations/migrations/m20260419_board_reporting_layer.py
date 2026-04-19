"""Board reporting layer tables (snapshot-driven, tenant-scoped)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260419_board_reporting_layer"
DISPLAY_NAME = "board_reporting_layer"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "board_reports")


def apply(engine: Engine) -> bool:
    if table_exists(engine, "board_reports"):
        return False
    with engine.begin() as conn:
        conn.execute(
            text("""
            CREATE TABLE board_reports (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                period_key VARCHAR(32) NOT NULL,
                period_type VARCHAR(16) NOT NULL DEFAULT 'monthly',
                period_start DATETIME NOT NULL,
                period_end DATETIME NOT NULL,
                title VARCHAR(500) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'generated',
                generated_at_utc DATETIME NOT NULL,
                generated_by VARCHAR(255),
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX uq_board_reports_tenant_period "
                "ON board_reports (tenant_id, period_key)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX idx_board_reports_tenant_generated "
                "ON board_reports (tenant_id, generated_at_utc)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE board_report_snapshots (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                report_id VARCHAR(36) NOT NULL,
                snapshot_kind VARCHAR(32) NOT NULL DEFAULT 'full',
                payload_json JSON NOT NULL,
                created_at DATETIME NOT NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_board_report_snapshots_tenant_report "
                "ON board_report_snapshots (tenant_id, report_id)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE board_report_items (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                report_id VARCHAR(36) NOT NULL,
                item_type VARCHAR(32) NOT NULL,
                item_key VARCHAR(128) NOT NULL,
                label VARCHAR(255) NOT NULL,
                value_num FLOAT,
                value_text TEXT,
                unit VARCHAR(32),
                traffic_light VARCHAR(16),
                trend_direction VARCHAR(16),
                trend_delta FLOAT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_board_report_items_tenant_report "
                "ON board_report_items (tenant_id, report_id)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE board_report_actions (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                report_id VARCHAR(36) NOT NULL,
                action_title VARCHAR(500) NOT NULL,
                action_detail TEXT,
                owner VARCHAR(320),
                due_at DATETIME,
                status VARCHAR(32) NOT NULL DEFAULT 'open',
                priority VARCHAR(16) NOT NULL DEFAULT 'medium',
                source_type VARCHAR(64) NOT NULL DEFAULT 'board',
                source_id VARCHAR(64),
                created_at DATETIME NOT NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_board_report_actions_tenant_report "
                "ON board_report_actions (tenant_id, report_id)"
            )
        )

        conn.execute(
            text("""
            CREATE TABLE board_report_metric_history (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255) NOT NULL,
                report_id VARCHAR(36) NOT NULL,
                metric_key VARCHAR(128) NOT NULL,
                period_start DATETIME NOT NULL,
                period_end DATETIME NOT NULL,
                value_num FLOAT NOT NULL,
                created_at DATETIME NOT NULL
            )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX idx_board_report_metric_history_tenant_metric "
                "ON board_report_metric_history (tenant_id, metric_key, period_end)"
            )
        )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
