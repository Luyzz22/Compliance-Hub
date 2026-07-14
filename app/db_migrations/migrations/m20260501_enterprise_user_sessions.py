"""Add revocable user_sessions for the browser/BFF identity boundary."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260501_enterprise_user_sessions"
DISPLAY_NAME = "enterprise_user_sessions"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "user_sessions")


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False
    with engine.begin() as conn:
        conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id VARCHAR(36) PRIMARY KEY,
                    token_hash VARCHAR(64) NOT NULL UNIQUE,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    tenant_id VARCHAR(255) NOT NULL,
                    role VARCHAR(64) NOT NULL,
                    auth_method VARCHAR(32) NOT NULL DEFAULT 'password',
                    created_at_utc DATETIME NOT NULL,
                    last_seen_at_utc DATETIME NOT NULL,
                    expires_at_utc DATETIME NOT NULL,
                    revoked_at_utc DATETIME,
                    revoked_reason VARCHAR(128)
                )
            """)
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_active"
                " ON user_sessions (user_id, revoked_at_utc)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_user_sessions_tenant_expiry"
                " ON user_sessions (tenant_id, expires_at_utc)"
            )
        )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
