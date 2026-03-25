"""Feature-Flags und Usage-Events / Metriken."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.feature_flags import FeatureFlag, is_feature_enabled
from app.main import app
from app.repositories.usage_events import UsageEventRepository
from app.services.tenant_usage_metrics import compute_tenant_usage_metrics
from app.services.usage_event_logger import (
    GOVERNANCE_ACTION_CREATED,
    log_usage_event,
    usage_tracking_enabled,
)

client = TestClient(app)

ADV_A = "advisor-portfolio-a@example.com"
API_KEY = "board-kpi-key"
T1 = "adv-portfolio-tenant-1"


@pytest.fixture
def advisor_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "COMPLIANCEHUB_ADVISOR_IDS",
        f"{ADV_A},advisor-portfolio-b@example.com",
    )


def test_feature_flag_defaults_true() -> None:
    assert is_feature_enabled(FeatureFlag.advisor_workspace) is True
    assert is_feature_enabled(FeatureFlag.demo_seeding) is True
    assert is_feature_enabled(FeatureFlag.ai_governance_playbook) is True
    assert is_feature_enabled(FeatureFlag.cross_regulation_dashboard) is True


def test_feature_flag_disabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE", "false")
    assert is_feature_enabled(FeatureFlag.advisor_workspace) is False


def test_ai_governance_playbook_flag_disabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_GOVERNANCE_PLAYBOOK", "false")
    assert is_feature_enabled(FeatureFlag.ai_governance_playbook) is False


def test_cross_regulation_dashboard_flag_disabled_via_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD", "false")
    assert is_feature_enabled(FeatureFlag.cross_regulation_dashboard) is False


def test_advisor_portfolio_forbidden_when_feature_off(
    monkeypatch: pytest.MonkeyPatch,
    advisor_allowlist: None,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE", "0")
    r = client.get(
        f"/api/v1/advisors/{ADV_A}/tenants/portfolio",
        headers={"x-api-key": API_KEY, "x-advisor-id": ADV_A},
    )
    assert r.status_code == 403
    assert "advisor_workspace" in r.json()["detail"]


def test_usage_metrics_from_synthetic_events() -> None:
    tid = "usage-metrics-synth-1"
    s = SessionLocal()
    try:
        repo = UsageEventRepository(s)
        repo.insert(tid, "board_view_opened", {"x": 1})
        repo.insert(tid, "board_view_opened", {"x": 2})
        repo.insert(tid, "evidence_uploaded", {"id": "e1"})
        repo.insert(tid, "governance_action_created", {"id": "a1"})
        m = compute_tenant_usage_metrics(s, tid)
        assert m.tenant_id == tid
        assert m.board_views_last_30d == 2
        assert m.evidence_uploads_last_30d == 1
        assert m.actions_created_last_30d == 1
        assert m.last_active_at is not None
    finally:
        s.close()


def test_log_usage_event_respects_tracking_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_USAGE_TRACKING", "false")
    assert usage_tracking_enabled() is False
    tid = "usage-opt-out-1"
    s = SessionLocal()
    try:
        log_usage_event(s, tid, GOVERNANCE_ACTION_CREATED, {"id": "z"})
        m = compute_tenant_usage_metrics(s, tid)
        assert m.actions_created_last_30d == 0
    finally:
        s.close()


def test_get_tenant_usage_metrics_api() -> None:
    tid = "board-kpi-tenant"
    r = client.get(
        f"/api/v1/tenants/{tid}/usage-metrics",
        headers={"x-api-key": API_KEY, "x-tenant-id": tid},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == tid
    assert "board_views_last_30d" in body


def test_guided_setup_completed_dedupe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_USAGE_TRACKING", "true")
    tid = "dedupe-setup-tenant"
    s = SessionLocal()
    try:
        log_usage_event(
            s,
            tid,
            "guided_setup_completed",
            {},
            dedupe_same_type_hours=24,
        )
        log_usage_event(
            s,
            tid,
            "guided_setup_completed",
            {},
            dedupe_same_type_hours=24,
        )
        since = datetime.now(UTC) - timedelta(days=1)
        repo = UsageEventRepository(s)
        c = repo.count_by_type_since(tid, ["guided_setup_completed"], since=since)
        assert c.get("guided_setup_completed", 0) == 1
    finally:
        s.close()
