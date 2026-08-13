"""Additive migration for auditable LLM workload classification."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from app.db_migrations import run_all_db_migrations


def test_llm_call_data_class_migrates_legacy_table(tmp_path) -> None:
    db_path = tmp_path / "legacy-llm-metadata.db"
    engine = create_engine(
        f"sqlite+pysqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE llm_call_metadata (
                    id VARCHAR(36) PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL,
                    task_type VARCHAR(64) NOT NULL,
                    provider VARCHAR(32) NOT NULL,
                    model_id VARCHAR(128) NOT NULL,
                    prompt_length INTEGER NOT NULL,
                    response_length INTEGER NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    estimated_input_tokens INTEGER NOT NULL,
                    estimated_output_tokens INTEGER NOT NULL,
                    created_at_utc TIMESTAMP NOT NULL
                )
                """
            )
        )

    first = run_all_db_migrations(engine)
    assert "20260811_add_llm_call_data_class" in first.applied_ddl
    columns = {column["name"] for column in inspect(engine).get_columns("llm_call_metadata")}
    assert "data_class" in columns

    second = run_all_db_migrations(engine)
    assert "20260811_add_llm_call_data_class" in second.skipped_ledger
    engine.dispose()
