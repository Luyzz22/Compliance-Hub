"""Production runtime checks schema postconditions without attempting DDL."""

from __future__ import annotations

from unittest.mock import Mock

from app.db_migrations.runner import list_unsatisfied_db_migrations


def test_read_only_schema_gate_reports_only_unsatisfied_migrations(monkeypatch) -> None:
    satisfied = Mock(MIGRATION_ID="20260101_satisfied")
    satisfied.satisfied.return_value = True
    missing = Mock(MIGRATION_ID="20260102_missing")
    missing.satisfied.return_value = False
    monkeypatch.setattr(
        "app.db_migrations.runner.iter_migration_modules",
        lambda: [satisfied, missing],
    )
    engine = Mock()

    assert list_unsatisfied_db_migrations(engine) == ["20260102_missing"]
    satisfied.satisfied.assert_called_once_with(engine)
    missing.satisfied.assert_called_once_with(engine)
    assert not satisfied.apply.called
    assert not missing.apply.called


def test_every_registered_migration_has_a_read_only_postcondition() -> None:
    from app.db_migrations.discovery import iter_migration_modules

    missing = [
        str(module.MIGRATION_ID)
        for module in iter_migration_modules()
        if not callable(getattr(module, "satisfied", None))
    ]

    assert missing == []
