"""Add users and user_tenant_roles tables for identity management."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260407_add_users_and_roles"
DISPLAY_NAME = "add_users_and_roles_tables"


def satisfied(engine: Engine) -> bool:
    return table_exists(engine, "users") and table_exists(engine, "user_tenant_roles")


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False
    with engine.begin() as conn:
        if not table_exists(engine, "users"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(36) PRIMARY KEY,
                    email VARCHAR(320) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    display_name VARCHAR(255),
                    company VARCHAR(255),
                    language VARCHAR(8) NOT NULL DEFAULT 'de',
                    timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Berlin',
                    email_verified BOOLEAN NOT NULL DEFAULT 0,
                    email_verification_token VARCHAR(128),
                    password_reset_token VARCHAR(128),
                    password_reset_expires DATETIME,
                    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until DATETIME,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    sso_provider VARCHAR(64),
                    sso_subject VARCHAR(255),
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL
                )
            """)
            )
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)"))
        if not table_exists(engine, "user_tenant_roles"):
            conn.execute(
                text("""
                CREATE TABLE IF NOT EXISTS user_tenant_roles (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
                    tenant_id VARCHAR(255) NOT NULL,
                    role VARCHAR(64) NOT NULL DEFAULT 'viewer',
                    assigned_by VARCHAR(36),
                    created_at_utc DATETIME NOT NULL,
                    updated_at_utc DATETIME NOT NULL,
                    UNIQUE(user_id, tenant_id)
                )
            """)
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_user_tenant_roles_user"
                    " ON user_tenant_roles (user_id)"
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS idx_user_tenant_roles_tenant"
                    " ON user_tenant_roles (tenant_id)"
                )
            )
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
