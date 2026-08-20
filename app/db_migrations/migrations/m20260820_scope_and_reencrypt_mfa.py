"""Tenant-scope MFA rows and revoke legacy plaintext factors.

Existing factor rows cannot be assigned to one tenant safely for multi-tenant users and their
TOTP seeds were stored without cryptographic protection. The migration therefore revokes them;
affected users must enroll a new encrypted factor after deployment.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260820_scope_and_reencrypt_mfa"
DISPLAY_NAME = "scope_and_reencrypt_mfa"


def satisfied(engine: Engine) -> bool:
    return column_exists(engine, "mfa_factors", "tenant_id") and column_exists(
        engine,
        "mfa_backup_codes",
        "tenant_id",
    )


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "mfa_factors") or not table_exists(engine, "mfa_backup_codes"):
        return False
    if satisfied(engine):
        return False

    factors_missing = not column_exists(engine, "mfa_factors", "tenant_id")
    backup_codes_missing = not column_exists(engine, "mfa_backup_codes", "tenant_id")
    with engine.begin() as conn:
        if factors_missing:
            conn.execute(text("ALTER TABLE mfa_factors ADD COLUMN tenant_id VARCHAR(255)"))
        if backup_codes_missing:
            conn.execute(text("ALTER TABLE mfa_backup_codes ADD COLUMN tenant_id VARCHAR(255)"))
        conn.execute(text("DELETE FROM mfa_backup_codes"))
        conn.execute(text("DELETE FROM mfa_factors"))
        if inspect(engine).dialect.name == "postgresql":
            conn.execute(text("ALTER TABLE mfa_factors ALTER COLUMN tenant_id SET NOT NULL"))
            conn.execute(text("ALTER TABLE mfa_backup_codes ALTER COLUMN tenant_id SET NOT NULL"))
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_mfa_factors_tenant_id ON mfa_factors (tenant_id)"),
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_mfa_backup_codes_tenant_id "
                "ON mfa_backup_codes (tenant_id)",
            ),
        )
    logger.warning("db_migration revoked legacy plaintext MFA factors: %s", MIGRATION_ID)
    return True
