"""Persistent ledger of applied migrations (audit + skip fast path)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def ensure_schema_migrations_table(engine: Engine) -> None:
    ddl = text(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
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
        "SELECT 1 FROM schema_migrations WHERE id = :id LIMIT 1",
    )
    with engine.connect() as conn:
        row = conn.execute(stmt, {"id": migration_id}).first()
    return row is not None


def record_migration_applied(engine: Engine, migration_id: str, name: str) -> None:
    applied_at = datetime.now(UTC).isoformat()
    stmt = text(
        """
        INSERT INTO schema_migrations (id, name, applied_at)
        VALUES (:id, :name, :applied_at)
        """
    )
    with engine.begin() as conn:
        conn.execute(
            stmt,
            {"id": migration_id, "name": name, "applied_at": applied_at},
        )
    logger.info("schema_migrations recorded: %s", migration_id)
