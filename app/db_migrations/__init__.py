"""Additive DB migrations (idempotent DDL + optional ``schema_migrations`` ledger)."""

from __future__ import annotations

from app.db_migrations.migrations.m20260326_add_tenants_kritis_sector import apply as _apply_kritis
from app.db_migrations.runner import MigrationRunSummary, run_all_db_migrations


def migrate_add_tenants_kritis_sector(engine) -> bool:
    """Apply only the KRITIS-sector column migration (tests, legacy script)."""
    return _apply_kritis(engine)


__all__ = [
    "MigrationRunSummary",
    "migrate_add_tenants_kritis_sector",
    "run_all_db_migrations",
]
