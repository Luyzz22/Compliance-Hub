"""Production startup must never grant the application path implicit DDL authority."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.db_schema_startup import ensure_runtime_schema


def test_production_startup_is_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = Mock()
    create_all = Mock()
    migrate = Mock()
    monkeypatch.setattr("app.db_schema_startup.Base.metadata.create_all", create_all)
    monkeypatch.setattr("app.db_schema_startup.run_all_db_migrations", migrate)
    monkeypatch.setattr("app.db_schema_startup.list_orm_columns_missing_in_db", lambda _engine: [])
    monkeypatch.setattr("app.db_schema_startup.list_unsatisfied_db_migrations", lambda _engine: [])

    ensure_runtime_schema(engine, production=True)

    create_all.assert_not_called()
    migrate.assert_not_called()


def test_production_startup_fails_closed_on_any_schema_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = Mock()
    monkeypatch.setattr(
        "app.db_schema_startup.list_orm_columns_missing_in_db",
        lambda _engine: ["tenants.kritis_sector"],
    )
    monkeypatch.setattr(
        "app.db_schema_startup.list_unsatisfied_db_migrations",
        lambda _engine: ["20260326_add_tenants_kritis_sector"],
    )

    with pytest.raises(RuntimeError, match="not release-ready"):
        ensure_runtime_schema(engine, production=True)


def test_development_startup_retains_local_schema_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = Mock()
    create_all = Mock()
    migrate = Mock()
    monkeypatch.setattr("app.db_schema_startup.Base.metadata.create_all", create_all)
    monkeypatch.setattr("app.db_schema_startup.run_all_db_migrations", migrate)

    ensure_runtime_schema(engine, production=False)

    create_all.assert_called_once_with(bind=engine)
    migrate.assert_called_once_with(engine)
