"""Add materialized_from_suggestion_key + partial unique index for idempotent from-suggestion."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, index_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260426_governance_controls_materialized_suggestion_key"
DISPLAY_NAME = "governance_controls_materialized_suggestion_key"

IDX = "uq_gc_tenant_materialized_suggestion"


def satisfied(engine: Engine) -> bool:
    if not table_exists(engine, "governance_controls"):
        return True
    if not column_exists(engine, "governance_controls", "materialized_from_suggestion_key"):
        return False
    return index_exists(engine, "governance_controls", IDX)


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "governance_controls"):
        return False
    if satisfied(engine):
        return False

    ddl_ran = False

    if not column_exists(engine, "governance_controls", "materialized_from_suggestion_key"):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE governance_controls ADD COLUMN "
                    "materialized_from_suggestion_key VARCHAR(128)"
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE governance_controls
                    SET materialized_from_suggestion_key = substr(
                        json_extract(source_inputs_json, '$.materialized_from_suggestion'),
                        1, 128
                    )
                    WHERE json_extract(source_inputs_json, '$.materialized_from_suggestion')
                        IS NOT NULL
                    """
                )
            )
        ddl_ran = True

    if not index_exists(engine, "governance_controls", IDX):
        with engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX uq_gc_tenant_materialized_suggestion "
                    "ON governance_controls (tenant_id, materialized_from_suggestion_key) "
                    "WHERE materialized_from_suggestion_key IS NOT NULL"
                )
            )
        ddl_ran = True

    if ddl_ran:
        logger.info("db_migration applied: %s", MIGRATION_ID)
    return ddl_ran
