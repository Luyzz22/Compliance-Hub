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


def _is_create_schema_migrations_forbidden(exc: BaseException) -> bool:
    """Heuristic: CREATE TABLE schema_migrations failed due to privileges / read-only DB."""
    parts: list[str] = []
    seen: set[int] = set()
    e: BaseException | None = exc
    while e is not None and id(e) not in seen:
        seen.add(id(e))
        parts.append(str(e).lower())
        for arg in getattr(e, "args", ()):
            if isinstance(arg, str):
                parts.append(arg.lower())
        e = e.__cause__ or e.__context__
    blob = " ".join(parts)
    needles = (
        "permission denied",
        "insufficient privilege",
        "must be owner",
        "readonly database",
        "read-only",
        "read only",
        "not authorized",
        "access denied",
        "cannot execute create",
        "create command denied",
        "denied for",
        "only select",
        "cannot create",
    )
    return any(n in blob for n in needles)


def _try_enable_ledger(engine: Engine) -> bool:
    """Return True if ``schema_migrations`` exists or was created; False if ledger is unusable."""
    try:
        ensure_schema_migrations_table(engine)
        return True
    except Exception as e:
        if _is_create_schema_migrations_forbidden(e):
            logger.warning(
                "DB migrations ledger disabled: cannot ensure schema_migrations table (%s). "
                "Ledgerless mode: no DDL and no ledger I/O from this role; run migrations "
                "with a privileged role if needed. Only satisfied() checks run here.",
                e,
            )
            return False
        raise


@dataclass
class MigrationRunSummary:
    """Outcome of a single ``run_all_db_migrations`` pass."""

    ledger_available: bool = True
    """False if ``schema_migrations`` could not be created (restricted DB role)."""

    applied_ddl: list[str] = field(default_factory=list)
    """Migration ids that executed DDL in this run."""

    skipped_ledger: list[str] = field(default_factory=list)
    """Ids skipped because already recorded in ``schema_migrations``."""

    ledger_backfilled: list[str] = field(default_factory=list)
    """Ids recorded without DDL (schema already satisfied, e.g. fresh ``create_all``)."""

    ledgerless_unsatisfied: list[str] = field(default_factory=list)
    """In ledgerless mode: migrations whose ``satisfied()`` is false (DBA action needed)."""


def run_all_db_migrations(engine: Engine) -> MigrationRunSummary:
    """Run all discoverable migrations in stable order.

    **Ledger mode** (default): the app role can ``CREATE TABLE schema_migrations``. The ledger
    records applied migrations; ``apply()`` may run additive DDL when the schema lags.

    **Ledgerless mode**: creating ``schema_migrations`` failed with a permission/read-only style
    error. This role does **not** execute ``apply()`` (no DDL) and does **not** read or write the
    ledger. Only ``satisfied(engine)`` is evaluated per migration; if any returns false, the id is
    listed in ``ledgerless_unsatisfied`` and a warning is logged — DBAs must align the schema.
    CI still catches ORM drift via ``list_orm_columns_missing_in_db`` on a full-permission DB.
    """
    summary = MigrationRunSummary()
    ledger_ok = _try_enable_ledger(engine)
    summary.ledger_available = ledger_ok

    if not ledger_ok:
        for mod in iter_migration_modules():
            mid = str(mod.MIGRATION_ID)
            satisfied_fn = getattr(mod, "satisfied", None)
            if callable(satisfied_fn) and satisfied_fn(engine):
                logger.debug("ledgerless: migration satisfied (no DDL from this role): %s", mid)
                continue
            summary.ledgerless_unsatisfied.append(mid)
            logger.warning(
                "ledgerless: migration %s not satisfied — schema may need DBA-applied DDL",
                mid,
            )
        return summary

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
