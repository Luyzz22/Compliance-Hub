"""API: Mandanten-Governance-Snapshot für Berater (Zuordnung, Feature-Flag)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.repositories.advisor_tenants import AdvisorTenantRepository

client = TestClient(app)

ADV_SN = "advisor-snap@example.com"
API_KEY = "board-kpi-key"
T_LINKED = "adv-snap-tenant-linked"
T_OTHER = "adv-snap-tenant-other"


@pytest.fixture
def advisor_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ADVISOR_IDS", ADV_SN)


def _h() -> dict[str, str]:
    return {"x-api-key": API_KEY, "x-advisor-id": ADV_SN}


def _seed() -> None:
    s = SessionLocal()
    try:
        AdvisorTenantRepository(s).upsert_link(
            advisor_id=ADV_SN,
            tenant_id=T_LINKED,
            tenant_display_name="Snap Mandant GmbH",
            industry="Chemie",
            country="DE",
        )
    finally:
        s.close()


def test_governance_snapshot_forbidden_when_feature_off(
    advisor_allowlist: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_CLIENT_SNAPSHOT", "false")
    _seed()
    r = client.get(
        f"/api/v1/advisors/{ADV_SN}/tenants/{T_LINKED}/governance-snapshot",
        headers=_h(),
    )
    assert r.status_code == 403
    assert "advisor_client_snapshot" in r.json()["detail"]


def test_governance_snapshot_404_when_not_linked(
    advisor_allowlist: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_CLIENT_SNAPSHOT", "true")
    r = client.get(
        f"/api/v1/advisors/{ADV_SN}/tenants/{T_OTHER}/governance-snapshot",
        headers=_h(),
    )
    assert r.status_code == 404


def test_governance_snapshot_200_structure(
    advisor_allowlist: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_CLIENT_SNAPSHOT", "true")
    _seed()
    r = client.post(
        "/api/v1/ai-systems",
        json={
            "id": "snap-sys-1",
            "name": "HR Bot",
            "description": "d",
            "business_unit": "HR",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "criticality": "very_high",
            "data_sensitivity": "internal",
        },
        headers={"x-api-key": API_KEY, "x-tenant-id": T_LINKED},
    )
    assert r.status_code == 200, r.text

    r2 = client.get(
        f"/api/v1/advisors/{ADV_SN}/tenants/{T_LINKED}/governance-snapshot",
        headers=_h(),
    )
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["client_tenant_id"] == T_LINKED
    assert body["advisor_id"] == ADV_SN
    assert body["client_info"]["tenant_id"] == T_LINKED
    assert body["ai_systems_summary"]["total_count"] >= 1
    assert body["ai_systems_summary"]["high_risk_count"] >= 1
    assert body["ai_systems_summary"]["nis2_critical_count"] >= 1


def test_governance_snapshot_report_403_when_llm_disabled(
    advisor_allowlist: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_CLIENT_SNAPSHOT", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "false")
    _seed()
    r = client.post(
        f"/api/v1/advisors/{ADV_SN}/tenants/{T_LINKED}/governance-snapshot-report",
        headers=_h(),
    )
    assert r.status_code == 403
