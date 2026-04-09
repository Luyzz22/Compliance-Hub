"""Allow NULL tenant_id on compliance_deadlines for global system deadlines (is_system)."""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260417_compliance_deadlines_tenant_id_nullable"
DISPLAY_NAME = "compliance_deadlines_tenant_id_nullable"

_IDX_TENANT_DUE = "idx_compliance_deadlines_tenant_due_date"
_IDX_SEED_UNIQUE = "uq_compliance_deadlines_tenant_source"


def _tenant_id_nullable(engine: Engine) -> bool:
    insp = inspect(engine)
    if not insp.has_table("compliance_deadlines"):
        return True
    for col in insp.get_columns("compliance_deadlines"):
        if col["name"] == "tenant_id":
            return bool(col.get("nullable", True))
    return True


def satisfied(engine: Engine) -> bool:
    if not table_exists(engine, "compliance_deadlines"):
        return True
    return _tenant_id_nullable(engine)


def _sqlite_rebuild_nullable_tenant_id(conn: Connection) -> None:
    conn.execute(text(f"DROP INDEX IF EXISTS {_IDX_TENANT_DUE}"))
    conn.execute(text(f"DROP INDEX IF EXISTS {_IDX_SEED_UNIQUE}"))
    conn.execute(
        text(
            """
            CREATE TABLE compliance_deadlines__tid_null (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                tenant_id VARCHAR(255),
                title VARCHAR(500) NOT NULL,
                description TEXT,
                category VARCHAR(32) NOT NULL,
                due_date VARCHAR(10) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'open',
                owner VARCHAR(320),
                regulation_reference VARCHAR(255),
                recurrence_months INTEGER,
                is_system INTEGER NOT NULL DEFAULT 0,
                source_type VARCHAR(64),
                source_id VARCHAR(128),
                created_at_utc DATETIME NOT NULL
            )
            """
        )
    )
    rows = conn.execute(text("PRAGMA table_info(compliance_deadlines)")).fetchall()
    col_names = [r[1] for r in sorted(rows, key=lambda x: x[0])]
    cols_sql = ", ".join(col_names)
    conn.execute(
        text(
            f"INSERT INTO compliance_deadlines__tid_null ({cols_sql}) "
            f"SELECT {cols_sql} FROM compliance_deadlines"
        )
    )
    conn.execute(text("DROP TABLE compliance_deadlines"))
    conn.execute(text("ALTER TABLE compliance_deadlines__tid_null RENAME TO compliance_deadlines"))
    conn.execute(
        text(f"CREATE INDEX {_IDX_TENANT_DUE} ON compliance_deadlines (tenant_id, due_date)")
    )
    conn.execute(
        text(
            f"CREATE UNIQUE INDEX {_IDX_SEED_UNIQUE} ON compliance_deadlines "
            "(tenant_id, source_type, source_id) "
            "WHERE source_type IS NOT NULL AND source_id IS NOT NULL"
        )
    )


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "compliance_deadlines"):
        return False
    if _tenant_id_nullable(engine):
        return False
    dialect = inspect(engine).dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text("ALTER TABLE compliance_deadlines ALTER COLUMN tenant_id DROP NOT NULL")
            )
        elif dialect == "sqlite":
            _sqlite_rebuild_nullable_tenant_id(conn)
        else:
            logger.warning(
                "db_migration %s: unsupported dialect %s for tenant_id nullable; skipped",
                MIGRATION_ID,
                dialect,
            )
            return False
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
