"""Persistent ledger of applied migrations (audit + skip fast path)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

SCHEMA_MIGRATIONS_TABLE = "schema_migrations"


def ensure_schema_migrations_table(engine: Engine) -> None:
    ddl = text(
        f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA_MIGRATIONS_TABLE} (
            id VARCHAR(128) PRIMARY KEY NOT NULL,
            name VARCHAR(255) NOT NULL,
            applied_at VARCHAR(64) NOT NULL
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(ddl)
    logger.debug("schema_migrations table ensured")


def has_migration_record(engine: Engine, migration_id: str) -> bool:
    stmt = text(
        f"SELECT 1 FROM {SCHEMA_MIGRATIONS_TABLE} WHERE id = :id LIMIT 1",
    )
    with engine.connect() as conn:
        row = conn.execute(stmt, {"id": migration_id}).first()
    return row is not None


def record_migration_applied(engine: Engine, migration_id: str, name: str) -> None:
    applied_at = datetime.now(UTC).isoformat()
    stmt = text(
        f"""
        INSERT INTO {SCHEMA_MIGRATIONS_TABLE} (id, name, applied_at)
        VALUES (:id, :name, :applied_at)
        """
    )
    with engine.begin() as conn:
        conn.execute(
            stmt,
            {"id": migration_id, "name": name, "applied_at": applied_at},
        )
    logger.info("schema_migrations recorded: %s", migration_id)
