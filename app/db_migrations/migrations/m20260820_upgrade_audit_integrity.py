"""Version the audit hash and enforce append-only storage at database level."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260820_upgrade_audit_integrity"
DISPLAY_NAME = "upgrade_audit_integrity"


def _trigger_exists(engine: Engine) -> bool:
    dialect = engine.dialect.name
    with engine.connect() as conn:
        if dialect == "postgresql":
            return bool(
                conn.execute(
                    text(
                        "SELECT 1 FROM pg_trigger "
                        "WHERE tgname = 'trg_audit_logs_append_only' AND NOT tgisinternal",
                    ),
                ).scalar_one_or_none(),
            )
        if dialect == "sqlite":
            count = conn.execute(
                text(
                    "SELECT count(*) FROM sqlite_master WHERE type='trigger' "
                    "AND name IN ('trg_audit_logs_no_update', 'trg_audit_logs_no_delete')",
                ),
            ).scalar_one()
            return int(count) == 2
    return True


def satisfied(engine: Engine) -> bool:
    return column_exists(engine, "audit_logs", "integrity_version") and _trigger_exists(engine)


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "audit_logs"):
        return False
    changed = False
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if not column_exists(engine, "audit_logs", "integrity_version"):
            conn.execute(
                text(
                    "ALTER TABLE audit_logs ADD COLUMN integrity_version VARCHAR(32) "
                    "NOT NULL DEFAULT 'sha256-v1'",
                ),
            )
            changed = True
        if dialect == "postgresql":
            conn.execute(
                text(
                    "ALTER TABLE audit_logs ALTER COLUMN integrity_version SET DEFAULT 'sha256-v2'",
                ),
            )
            conn.execute(
                text(
                    "CREATE OR REPLACE FUNCTION compliancehub_reject_audit_mutation() "
                    "RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN "
                    "RAISE EXCEPTION 'audit_logs is append-only'; END; $$",
                ),
            )
            conn.execute(text("DROP TRIGGER IF EXISTS trg_audit_logs_append_only ON audit_logs"))
            conn.execute(
                text(
                    "CREATE TRIGGER trg_audit_logs_append_only BEFORE UPDATE OR DELETE "
                    "ON audit_logs FOR EACH ROW EXECUTE FUNCTION "
                    "compliancehub_reject_audit_mutation()",
                ),
            )
            changed = True
        elif dialect == "sqlite":
            conn.execute(
                text(
                    "CREATE TRIGGER IF NOT EXISTS trg_audit_logs_no_update "
                    "BEFORE UPDATE ON audit_logs BEGIN "
                    "SELECT RAISE(ABORT, 'audit_logs is append-only'); END",
                ),
            )
            conn.execute(
                text(
                    "CREATE TRIGGER IF NOT EXISTS trg_audit_logs_no_delete "
                    "BEFORE DELETE ON audit_logs BEGIN "
                    "SELECT RAISE(ABORT, 'audit_logs is append-only'); END",
                ),
            )
            changed = True
    if changed:
        logger.info("db_migration applied: %s", MIGRATION_ID)
    return changed
