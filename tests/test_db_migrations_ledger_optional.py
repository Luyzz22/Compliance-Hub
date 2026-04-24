"""Optional schema_migrations ledger: restricted roles skip CREATE TABLE without failing startup."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from app.db_migrations.runner import _is_create_schema_migrations_forbidden, run_all_db_migrations
from app.models_db import Base


def test_is_create_schema_migrations_forbidden_detects_privilege_messages() -> None:
    assert _is_create_schema_migrations_forbidden(
        OperationalError("stmt", {}, Exception("permission denied for schema public"))
    )
    assert _is_create_schema_migrations_forbidden(
        OperationalError("stmt", {}, Exception("attempt to write a readonly database"))
    )
    assert not _is_create_schema_migrations_forbidden(
        OperationalError("stmt", {}, Exception("no such table: foo"))
    )


def test_run_all_ledgerless_does_not_raise_and_skips_ddl_when_ensure_fails(
    tmp_path,
) -> None:
    db_path = tmp_path / "ledgerless_ok.db"
    url = f"sqlite+pysqlite:///{db_path}"
    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    def _deny_ensure(_e) -> None:
        raise OperationalError(
            "CREATE TABLE schema_migrations",
            {},
            Exception("permission denied for schema public"),
        )

    with patch("app.db_migrations.runner.ensure_schema_migrations_table", _deny_ensure):
        summary = run_all_db_migrations(engine)

    assert summary.ledger_available is False
    assert summary.applied_ddl == []
    assert summary.skipped_ledger == []
    assert summary.ledger_backfilled == []
    assert summary.ledgerless_unsatisfied == []

    assert not inspect(engine).has_table("schema_migrations")
    engine.dispose()


def test_run_all_ledgerless_reports_unsatisfied_without_ddl(tmp_path) -> None:
    """Legacy schema missing a column: ledgerless mode must not ALTER; list unsatisfied ids."""
    db_path = tmp_path / "ledgerless_legacy.db"
    url = f"sqlite+pysqlite:///{db_path}"
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

    def _deny_ensure(_e) -> None:
        raise OperationalError(
            "CREATE TABLE",
            {},
            Exception("insufficient privilege"),
        )

    with patch("app.db_migrations.runner.ensure_schema_migrations_table", _deny_ensure):
        summary = run_all_db_migrations(engine)

    assert summary.ledger_available is False
    assert summary.applied_ddl == []
    ids = summary.ledgerless_unsatisfied
    assert "20260326_add_tenants_kritis_sector" in ids
    assert "20260327_add_tenant_ai_governance_setup_notes" in ids
    assert "20260328_add_ai_runtime_events_tenant_system_time_idx" in ids
    assert "20260329_add_ai_runtime_events_event_subtype" in ids
    assert "20260406_add_audit_log_gobd_fields" in ids
    assert "20260407_add_ai_systems_ki_register_fields" in ids
    assert "20260407_audit_log_structured_fields" in ids
    assert "20260408_nis2_final_report_deadline" in ids
    assert "20260409_compliance_deadlines_source_and_index" in ids
    assert "20260407_add_users_and_roles" in ids
    assert "20260411_enterprise_iam_tables" in ids
    assert "20260412_governance_mfa_sod_approvals" in ids
    assert "20260413_phase3_reporting_datev_rag" in ids
    assert "20260414_phase4_pdf_xrechnung" in ids
    assert "20260415_phase5_onboarding_billing" in ids
    assert "20260416_phase7_compliance_calendar_system_deadlines" in ids
    assert "20260418_phase10_audit_alerts" in ids
    assert "20260419_trust_center_assurance_portal" in ids
    assert "20260420_phase11_trust_center_esigning" in ids
    assert "20260421_phase12_esigning_key_rotation" in ids
    assert "20260422_phase13_tenant_onboarding_completed" in ids
    assert "20260423_phase14_analytics_indexes" in ids
    assert "20260424_service_health_operational_resilience" in ids
    assert "20260425_governance_unified_controls" in ids
    assert "20260427_governance_audit_readiness" in ids
    assert "20260419_board_reporting_layer" in ids
    assert "20260428_remediation_actions_layer" in ids
    assert "20260429_remediation_automation_layer" in ids
    assert len(ids) == 28
    cols = {c["name"] for c in inspect(engine).get_columns("tenants")}
    assert "kritis_sector" not in cols
    engine.dispose()


def test_ensure_failure_non_privilege_still_raises(tmp_path) -> None:
    db_path = tmp_path / "ledger_boom.db"
    url = f"sqlite+pysqlite:///{db_path}"
    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    def _boom(_e) -> None:
        raise RuntimeError("unexpected catalog corruption")

    with patch("app.db_migrations.runner.ensure_schema_migrations_table", _boom):
        with pytest.raises(RuntimeError, match="catalog corruption"):
            run_all_db_migrations(engine)
    engine.dispose()
