"""Regression: system deadlines need NULL tenant_id after upgrade from NOT NULL schema."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.db_migrations.migrations import m20260417_compliance_deadlines_tenant_id_nullable as m17


def _legacy_compliance_deadlines_ddl() -> str:
    return """
    CREATE TABLE compliance_deadlines (
        id VARCHAR(36) NOT NULL PRIMARY KEY,
        tenant_id VARCHAR(255) NOT NULL,
        title VARCHAR(500) NOT NULL,
        description TEXT,
        category VARCHAR(32) NOT NULL,
        due_date VARCHAR(10) NOT NULL,
        status VARCHAR(32) NOT NULL DEFAULT 'open',
        owner VARCHAR(320),
        regulation_reference VARCHAR(255),
        recurrence_months INTEGER,
        is_system INTEGER NOT NULL DEFAULT 0,
        source_type VARCHAR(64),
        source_id VARCHAR(128),
        created_at_utc DATETIME NOT NULL
    );
    """


def test_m20260417_sqlite_allows_null_tenant_after_rebuild(tmp_path: Path) -> None:
    db_path = tmp_path / "tenant_null.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as conn:
        conn.execute(text(_legacy_compliance_deadlines_ddl()))

    assert m17.satisfied(engine) is False
    assert m17.apply(engine) is True
    assert m17.satisfied(engine) is True

    tenant_col = next(
        c for c in inspect(engine).get_columns("compliance_deadlines") if c["name"] == "tenant_id"
    )
    assert tenant_col["nullable"] is True

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO compliance_deadlines (
                    id, tenant_id, title, category, due_date, status,
                    is_system, source_type, source_id, created_at_utc
                ) VALUES (
                    'sys-deadline-test-1', NULL, 'DACH System', 'nis2', '2026-08-02', 'open',
                    1, 'system_catalog', 'eu-ai-act-high-risk', datetime('now')
                )
                """
            )
        )
    engine.dispose()
