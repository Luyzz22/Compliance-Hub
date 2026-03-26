"""Execute registered migrations in order; optional ``schema_migrations`` ledger."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.engine import Engine

from app.db_migrations.discovery import iter_migration_modules
from app.db_migrations.schema_tracking import (
    ensure_schema_migrations_table,
    has_migration_record,
    record_migration_applied,
)

logger = logging.getLogger(__name__)


@dataclass
class MigrationRunSummary:
    """Outcome of a single ``run_all_db_migrations`` pass."""

    applied_ddl: list[str] = field(default_factory=list)
    """Migration ids that executed DDL in this run."""

    skipped_ledger: list[str] = field(default_factory=list)
    """Ids skipped because already recorded in ``schema_migrations``."""

    ledger_backfilled: list[str] = field(default_factory=list)
    """Ids recorded without DDL (schema already satisfied, e.g. fresh ``create_all``)."""


def run_all_db_migrations(engine: Engine) -> MigrationRunSummary:
    """Run all discoverable migrations in stable order.

    Each module under ``app.db_migrations.migrations`` exposes ``MIGRATION_ID`` and
    ``apply(engine) -> bool``. Optional ``satisfied(engine) -> bool`` backfills the
    ledger when the schema is already correct without DDL.

    The ``schema_migrations`` table stores ids after successful DDL or backfill so
    later runs can skip quickly (inspect remains the source of truth for idempotent
    ``apply()`` when the ledger is missing).
    """
    summary = MigrationRunSummary()
    ensure_schema_migrations_table(engine)

    for mod in iter_migration_modules():
        mid = str(mod.MIGRATION_ID)
        display = str(getattr(mod, "DISPLAY_NAME", mid))

        if has_migration_record(engine, mid):
            summary.skipped_ledger.append(mid)
            logger.info("migration skipped (ledger): %s", mid)
            continue

        ddl_ran = bool(mod.apply(engine))
        if ddl_ran:
            record_migration_applied(engine, mid, display)
            summary.applied_ddl.append(mid)
            continue

        satisfied_fn = getattr(mod, "satisfied", None)
        if callable(satisfied_fn) and satisfied_fn(engine):
            record_migration_applied(engine, mid, display)
            summary.ledger_backfilled.append(mid)
            logger.info("migration ledger backfilled (schema already satisfied): %s", mid)
        else:
            logger.debug("migration deferred (no DDL, not satisfied): %s", mid)

    return summary
