"""Regression: ORM columns on existing ``tenants`` rows need additive migrations."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.db_migrations import migrate_add_tenants_kritis_sector, run_all_db_migrations
from app.db_migrations.schema_alignment import list_orm_columns_missing_in_db
from app.models_db import TenantDB


def _create_legacy_tenants_table_without_kritis(url: str) -> None:
    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    ddl = """
    CREATE TABLE tenants (
        id VARCHAR(255) PRIMARY KEY,
        display_name VARCHAR(255) NOT NULL,
        industry VARCHAR(128) NOT NULL,
        country VARCHAR(64) NOT NULL DEFAULT 'DE',
        nis2_scope VARCHAR(64) NOT NULL DEFAULT 'in_scope',
        ai_act_scope VARCHAR(64) NOT NULL DEFAULT 'in_scope',
        is_demo BOOLEAN NOT NULL DEFAULT 0,
        demo_playground BOOLEAN NOT NULL DEFAULT 0,
        created_at_utc DATETIME NOT NULL
    )
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    engine.dispose()


def test_migrate_adds_kritis_sector_idempotent(tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    url = f"sqlite+pysqlite:///{db_path}"
    _create_legacy_tenants_table_without_kritis(url)

    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    assert "tenants.kritis_sector" in list_orm_columns_missing_in_db(
        engine, require_all_tables=False
    )
    assert migrate_add_tenants_kritis_sector(engine) is True
    assert migrate_add_tenants_kritis_sector(engine) is False

    cols = {c["name"]: c for c in inspect(engine).get_columns("tenants")}
    assert "kritis_sector" in cols

    with Session(engine) as session:
        row = TenantDB(
            id="legacy-tenant-1",
            display_name="Legacy AG",
            industry="IT",
            country="DE",
            nis2_scope="in_scope",
            kritis_sector="energy",
            ai_act_scope="in_scope",
            is_demo=False,
            demo_playground=False,
            created_at_utc=datetime(2025, 1, 1, tzinfo=UTC),
        )
        session.add(row)
        session.commit()
        loaded = session.get(TenantDB, "legacy-tenant-1")
        assert loaded is not None
        assert loaded.kritis_sector == "energy"

    post = run_all_db_migrations(engine)
    # New migrations (e.g. users/roles) may apply DDL on first run.
    assert "20260326_add_tenants_kritis_sector" not in post.applied_ddl
    assert "20260326_add_tenants_kritis_sector" in post.ledger_backfilled
    assert "tenants.kritis_sector" not in list_orm_columns_missing_in_db(
        engine, require_all_tables=False
    )

    again = run_all_db_migrations(engine)
    assert again.applied_ddl == []
    assert "20260326_add_tenants_kritis_sector" in again.skipped_ledger
    engine.dispose()


def test_run_all_migrations_reports_applied_once(tmp_path) -> None:
    db_path = tmp_path / "legacy2.db"
    url = f"sqlite+pysqlite:///{db_path}"
    _create_legacy_tenants_table_without_kritis(url)

    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    first = run_all_db_migrations(engine)
    assert "20260326_add_tenants_kritis_sector" in first.applied_ddl
    second = run_all_db_migrations(engine)
    assert second.applied_ddl == []
    assert "20260326_add_tenants_kritis_sector" in second.skipped_ledger
    engine.dispose()
