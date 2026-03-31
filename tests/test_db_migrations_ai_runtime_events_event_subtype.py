"""Regression: nullable event_subtype on ai_runtime_events."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.db_migrations import run_all_db_migrations
from app.db_migrations.util import column_exists
from app.models_db import AiRuntimeEventTable

MID = "20260329_add_ai_runtime_events_event_subtype"


def _create_legacy_ai_runtime_events_without_subtype(url: str) -> None:
    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    ddl = """
    CREATE TABLE ai_runtime_events (
        id VARCHAR(36) PRIMARY KEY,
        tenant_id VARCHAR(255) NOT NULL,
        ai_system_id VARCHAR(255) NOT NULL,
        source VARCHAR(64) NOT NULL,
        source_event_id VARCHAR(128) NOT NULL,
        event_type VARCHAR(64) NOT NULL,
        severity VARCHAR(32),
        metric_key VARCHAR(128),
        incident_code VARCHAR(128),
        value FLOAT,
        delta FLOAT,
        threshold_breached BOOLEAN,
        environment VARCHAR(64),
        model_version VARCHAR(255),
        occurred_at DATETIME NOT NULL,
        received_at DATETIME NOT NULL,
        extra TEXT NOT NULL DEFAULT '{}'
    )
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    engine.dispose()


def test_event_subtype_migration_orm_and_idempotent(tmp_path) -> None:
    db_path = tmp_path / "aire_subtype.db"
    url = f"sqlite+pysqlite:///{db_path}"
    _create_legacy_ai_runtime_events_without_subtype(url)

    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    assert not column_exists(engine, "ai_runtime_events", "event_subtype")

    first = run_all_db_migrations(engine)
    assert MID in first.applied_ddl
    assert column_exists(engine, "ai_runtime_events", "event_subtype")

    cols = {c["name"]: c for c in inspect(engine).get_columns("ai_runtime_events")}
    assert cols["event_subtype"]["nullable"] is True

    eid = str(uuid.uuid4())
    now = datetime(2025, 3, 1, 12, 0, 0, tzinfo=UTC)
    with Session(engine) as session:
        row = AiRuntimeEventTable(
            id=eid,
            tenant_id="t-sub",
            ai_system_id="sys-sub",
            source="sap_ai_core",
            source_event_id="src-1",
            event_type="incident",
            event_subtype="drift_high",
            occurred_at=now,
            received_at=now,
            extra={},
        )
        session.add(row)
        session.commit()
        loaded = session.get(AiRuntimeEventTable, eid)
        assert loaded is not None
        assert loaded.event_subtype == "drift_high"

    second = run_all_db_migrations(engine)
    assert second.applied_ddl == []
    assert MID in second.skipped_ledger

    engine.dispose()
