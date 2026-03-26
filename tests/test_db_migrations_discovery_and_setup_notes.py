"""Discovery rules, template exclusion, and ``setup_notes`` additive migration."""

from __future__ import annotations

import logging
import pkgutil
from datetime import UTC, datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

import app.db_migrations.migrations as migrations_pkg
from app.db_migrations import run_all_db_migrations
from app.db_migrations.discovery import iter_migration_modules
from app.models_db import TenantAIGovernanceSetupDB


def test_template_module_exposes_copy_paste_string() -> None:
    from app.db_migrations.migrations import _template_example as t

    assert "MIGRATION_ID" in t.MIGRATION_TEMPLATE
    assert "def apply" in t.MIGRATION_TEMPLATE


def test_discovery_skips_underscore_prefixed_modules() -> None:
    names = [n for _f, n, _p in pkgutil.iter_modules(migrations_pkg.__path__)]
    assert "_template_example" in names
    loaded = [m.__name__.rsplit(".", 1)[-1] for m in iter_migration_modules()]
    assert "_template_example" not in loaded
    assert "m20260326_add_tenants_kritis_sector" in loaded
    assert "m20260327_add_tenant_ai_governance_setup_notes" in loaded


def test_migration_ids_are_sorted() -> None:
    ids = [m.MIGRATION_ID for m in iter_migration_modules()]
    assert ids == sorted(ids)


def _create_legacy_setup_table_without_notes(url: str) -> None:
    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    ddl = """
    CREATE TABLE tenant_ai_governance_setup (
        tenant_id VARCHAR(255) PRIMARY KEY,
        payload TEXT NOT NULL,
        updated_at_utc DATETIME NOT NULL
    )
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    engine.dispose()


def test_setup_notes_migration_logs_applied_and_skips_ledger(tmp_path, caplog) -> None:
    db_path = tmp_path / "setup_notes.db"
    url = f"sqlite+pysqlite:///{db_path}"
    _create_legacy_setup_table_without_notes(url)

    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    caplog.set_level(
        logging.INFO,
        logger="app.db_migrations.migrations.m20260327_add_tenant_ai_governance_setup_notes",
    )

    first = run_all_db_migrations(engine)
    assert "20260327_add_tenant_ai_governance_setup_notes" in first.applied_ddl
    assert "db_migration applied: 20260327_add_tenant_ai_governance_setup_notes" in caplog.text

    cols = {c["name"] for c in inspect(engine).get_columns("tenant_ai_governance_setup")}
    assert "setup_notes" in cols

    with Session(engine) as session:
        row = TenantAIGovernanceSetupDB(
            tenant_id="t-setup-1",
            payload={},
            setup_notes="smoke",
            updated_at_utc=datetime(2025, 6, 1, tzinfo=UTC),
        )
        session.add(row)
        session.commit()
        loaded = session.get(TenantAIGovernanceSetupDB, "t-setup-1")
        assert loaded is not None
        assert loaded.setup_notes == "smoke"

    second = run_all_db_migrations(engine)
    assert second.applied_ddl == []
    assert "20260327_add_tenant_ai_governance_setup_notes" in second.skipped_ledger
    engine.dispose()
