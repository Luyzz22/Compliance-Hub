"""Add final_report_deadline to nis2_incidents (NIS2-style follow-on reporting window)."""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260408_nis2_final_report_deadline"
DISPLAY_NAME = "nis2_final_report_deadline"


def satisfied(engine: Engine) -> bool:
    return column_exists(engine, "nis2_incidents", "final_report_deadline")


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "nis2_incidents"):
        return False
    if satisfied(engine):
        return False
    dialect = inspect(engine).dialect.name
    col_type = "TIMESTAMP WITH TIME ZONE" if dialect == "postgresql" else "DATETIME"
    with engine.begin() as conn:
        conn.execute(
            text(f"ALTER TABLE nis2_incidents ADD COLUMN final_report_deadline {col_type}")
        )
        if dialect == "sqlite":
            conn.execute(
                text(
                    "UPDATE nis2_incidents SET final_report_deadline = "
                    "datetime(bsi_report_deadline, '+30 days') "
                    "WHERE final_report_deadline IS NULL AND bsi_report_deadline IS NOT NULL"
                )
            )
        else:
            conn.execute(
                text(
                    "UPDATE nis2_incidents SET final_report_deadline = "
                    "bsi_report_deadline + interval '30 days' "
                    "WHERE final_report_deadline IS NULL AND bsi_report_deadline IS NOT NULL"
                )
            )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
