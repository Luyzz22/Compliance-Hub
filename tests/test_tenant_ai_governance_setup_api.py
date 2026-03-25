"""API: AI-Governance-Setup-Wizard (Persistenz, Fortschritt, Feature-Flag)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    DataSensitivity,
)
from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _h(tenant_id: str) -> dict[str, str]:
    return {"x-api-key": "test-api-key", "x-tenant-id": tenant_id}


def test_ai_governance_setup_forbidden_when_feature_off(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_GOVERNANCE_SETUP_WIZARD", "false")
    tid = f"ags-ff-{uuid.uuid4().hex[:10]}"
    r = client.get(f"/api/v1/tenants/{tid}/ai-governance-setup", headers=_h(tid))
    assert r.status_code == 403
    assert "ai_governance_setup_wizard" in r.json()["detail"]


def test_ai_governance_setup_get_defaults_and_put_merge(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_GOVERNANCE_SETUP_WIZARD", "true")
    tid = f"ags-api-{uuid.uuid4().hex[:12]}"
    h = _h(tid)

    r0 = client.get(f"/api/v1/tenants/{tid}/ai-governance-setup", headers=h)
    assert r0.status_code == 200
    b0 = r0.json()
    assert b0["tenant_id"] == tid
    assert b0["tenant_kind"] is None
    assert b0["active_frameworks"] == []
    assert b0["progress_steps"] == []

    r1 = client.put(
        f"/api/v1/tenants/{tid}/ai-governance-setup",
        headers=h,
        json={
            "tenant_kind": "enterprise",
            "compliance_scopes": ["eu_ai_act_high_risk", "nis2"],
            "governance_roles": {"board": "cfo@example.com"},
            "active_frameworks": ["eu_ai_act", "iso_42001"],
            "mark_steps_complete": [1, 2],
        },
    )
    assert r1.status_code == 200, r1.text
    b1 = r1.json()
    assert b1["tenant_kind"] == "enterprise"
    assert "eu_ai_act_high_risk" in b1["compliance_scopes"]
    assert b1["governance_roles"]["board"] == "cfo@example.com"
    assert b1["active_frameworks"] == ["eu_ai_act", "iso_42001"]
    assert 1 in b1["progress_steps"] and 2 in b1["progress_steps"]

    r2 = client.put(
        f"/api/v1/tenants/{tid}/ai-governance-setup",
        headers=h,
        json={"governance_roles": {"ciso": "ciso@example.com"}, "mark_steps_complete": [2]},
    )
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["governance_roles"]["board"] == "cfo@example.com"
    assert b2["governance_roles"]["ciso"] == "ciso@example.com"


def test_ai_governance_setup_progress_infers_from_systems_and_kpis(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_GOVERNANCE_SETUP_WIZARD", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_KPI_KRI", "true")
    tid = f"ags-prg-{uuid.uuid4().hex[:12]}"
    h = _h(tid)
    sid = "ags-sys-1"

    client.put(
        f"/api/v1/tenants/{tid}/ai-governance-setup",
        headers=h,
        json={"tenant_kind": "advisor", "active_frameworks": ["nis2"]},
    )

    payload = {
        "id": sid,
        "name": "Wizard Test",
        "description": "d",
        "business_unit": "HR",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": True,
        "criticality": AISystemCriticality.high.value,
        "data_sensitivity": DataSensitivity.internal.value,
    }
    assert client.post("/api/v1/ai-systems", json=payload, headers=h).status_code == 200

    r3 = client.get(f"/api/v1/tenants/{tid}/ai-governance-setup", headers=h)
    assert r3.status_code == 200
    assert 1 in r3.json()["progress_steps"]
    assert 2 in r3.json()["progress_steps"]
    assert 3 in r3.json()["progress_steps"]

    r_list = client.get(f"/api/v1/tenants/{tid}/ai-systems/{sid}/kpis", headers=h)
    assert r_list.status_code == 200
    def_id = r_list.json()["series"][0]["definition"]["id"]
    r_k = client.post(
        f"/api/v1/tenants/{tid}/ai-systems/{sid}/kpis",
        headers=h,
        json={
            "kpi_definition_id": def_id,
            "period_start": "2025-01-01T00:00:00+00:00",
            "period_end": "2025-01-31T00:00:00+00:00",
            "value": 1.0,
            "source": "manual",
        },
    )
    assert r_k.status_code == 200, r_k.text

    r4 = client.get(f"/api/v1/tenants/{tid}/ai-governance-setup", headers=h)
    assert 4 in r4.json()["progress_steps"]
