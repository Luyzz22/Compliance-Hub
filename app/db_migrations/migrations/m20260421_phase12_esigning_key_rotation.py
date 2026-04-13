"""Phase 12: E-Signing Key-Rotation-Safe Verification & Payload-Binding columns."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260421_phase12_esigning_key_rotation"
DISPLAY_NAME = "phase12_esigning_key_rotation"


def satisfied(engine: Engine) -> bool:
    return column_exists(engine, "evidence_bundles", "signing_key_id") and column_exists(
        engine, "evidence_bundles", "signed_payload"
    )


def apply(engine: Engine) -> bool:
    if satisfied(engine):
        return False

    applied = False
    with engine.begin() as conn:
        if table_exists(engine, "evidence_bundles"):
            if not column_exists(engine, "evidence_bundles", "signing_key_id"):
                conn.execute(
                    text("ALTER TABLE evidence_bundles ADD COLUMN signing_key_id VARCHAR(64)")
                )
                applied = True
            if not column_exists(engine, "evidence_bundles", "signed_payload"):
                conn.execute(text("ALTER TABLE evidence_bundles ADD COLUMN signed_payload TEXT"))
                applied = True

    if applied:
        logger.info("db_migration applied: %s", MIGRATION_ID)
    return applied
