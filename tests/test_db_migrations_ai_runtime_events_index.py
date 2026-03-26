"""Regression: composite index on ai_runtime_events for tenant/system/time (OAMI / reporting)."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.db_migrations import run_all_db_migrations
from app.db_migrations.util import index_exists

INDEX_NAME = "ix_ai_runtime_events_tenant_system_time"
MID = "20260328_add_ai_runtime_events_tenant_system_time_idx"


def _create_minimal_ai_runtime_events_table(url: str) -> None:
    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    ddl = """
    CREATE TABLE ai_runtime_events (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(255) NOT NULL,
        ai_system_id VARCHAR(255) NOT NULL,
        occurred_at DATETIME NOT NULL
    )
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    engine.dispose()


def test_ai_runtime_events_time_index_applied_and_idempotent(tmp_path) -> None:
    db_path = tmp_path / "aire_idx.db"
    url = f"sqlite+pysqlite:///{db_path}"
    _create_minimal_ai_runtime_events_table(url)

    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    assert not index_exists(engine, "ai_runtime_events", INDEX_NAME)

    first = run_all_db_migrations(engine)
    assert MID in first.applied_ddl
    assert index_exists(engine, "ai_runtime_events", INDEX_NAME)

    idxs = inspect(engine).get_indexes("ai_runtime_events")
    names = {i["name"] for i in idxs}
    assert INDEX_NAME in names

    second = run_all_db_migrations(engine)
    assert second.applied_ddl == []
    assert MID in second.skipped_ledger
    assert index_exists(engine, "ai_runtime_events", INDEX_NAME)

    engine.dispose()
