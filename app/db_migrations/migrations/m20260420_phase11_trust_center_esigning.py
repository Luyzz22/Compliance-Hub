"""Phase 11: Evidence Bundle E-Signing + access log metadata columns."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260420_phase11_trust_center_esigning"
DISPLAY_NAME = "phase11_trust_center_esigning"


def satisfied(engine: Engine) -> bool:
    return (
        column_exists(engine, "evidence_bundles", "signature")
        and column_exists(engine, "evidence_bundles", "cert_fingerprint")
        and column_exists(engine, "evidence_bundles", "signed_at")
        and column_exists(engine, "evidence_bundles", "signed_by_role")
        and column_exists(engine, "trust_center_access_logs", "metadata_json")
    )


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False

    applied = False
    with engine.begin() as conn:
        if table_exists(engine, "evidence_bundles"):
            if not column_exists(engine, "evidence_bundles", "signature"):
                conn.execute(text("ALTER TABLE evidence_bundles ADD COLUMN signature TEXT"))
                applied = True
            if not column_exists(engine, "evidence_bundles", "cert_fingerprint"):
                conn.execute(
                    text("ALTER TABLE evidence_bundles ADD COLUMN cert_fingerprint VARCHAR(128)")
                )
                applied = True
            if not column_exists(engine, "evidence_bundles", "signed_at"):
                conn.execute(text("ALTER TABLE evidence_bundles ADD COLUMN signed_at DATETIME"))
                applied = True
            if not column_exists(engine, "evidence_bundles", "signed_by_role"):
                conn.execute(
                    text("ALTER TABLE evidence_bundles ADD COLUMN signed_by_role VARCHAR(64)")
                )
                applied = True

        if table_exists(engine, "trust_center_access_logs"):
            if not column_exists(engine, "trust_center_access_logs", "metadata_json"):
                conn.execute(
                    text("ALTER TABLE trust_center_access_logs ADD COLUMN metadata_json TEXT")
                )
                applied = True

    if applied:
        logger.info("db_migration applied: %s", MIGRATION_ID)
    return applied
