"""Compliance calendar: source linkage, tenant+due index, partial unique seed keys."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, index_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260409_compliance_deadlines_source_and_index"
DISPLAY_NAME = "compliance_deadlines_source_and_index"

_IDX_TENANT_DUE = "idx_compliance_deadlines_tenant_due_date"
_IDX_SEED_UNIQUE = "uq_compliance_deadlines_tenant_source"


def satisfied(engine: Engine) -> bool:
    if not table_exists(engine, "compliance_deadlines"):
        return False
    return (
        column_exists(engine, "compliance_deadlines", "source_type")
        and column_exists(engine, "compliance_deadlines", "source_id")
        and index_exists(engine, "compliance_deadlines", _IDX_TENANT_DUE)
        and index_exists(engine, "compliance_deadlines", _IDX_SEED_UNIQUE)
    )


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "compliance_deadlines"):
        return False
    changed = False
    with engine.begin() as conn:
        if not column_exists(engine, "compliance_deadlines", "source_type"):
            conn.execute(
                text("ALTER TABLE compliance_deadlines ADD COLUMN source_type VARCHAR(64)")
            )
            changed = True
        if not column_exists(engine, "compliance_deadlines", "source_id"):
            conn.execute(
                text("ALTER TABLE compliance_deadlines ADD COLUMN source_id VARCHAR(128)")
            )
            changed = True
        if not index_exists(engine, "compliance_deadlines", _IDX_TENANT_DUE):
            conn.execute(
                text(
                    f"CREATE INDEX {_IDX_TENANT_DUE} ON compliance_deadlines "
                    "(tenant_id, due_date)"
                )
            )
            changed = True
        if not index_exists(engine, "compliance_deadlines", _IDX_SEED_UNIQUE):
            conn.execute(
                text(
                    f"CREATE UNIQUE INDEX {_IDX_SEED_UNIQUE} ON compliance_deadlines "
                    "(tenant_id, source_type, source_id) "
                    "WHERE source_type IS NOT NULL AND source_id IS NOT NULL"
                )
            )
            changed = True
    if changed:
        logger.info("db_migration applied: %s", MIGRATION_ID)
    return changed
