"""Governance Maturity API (Readiness + GAI + OAMI)."""

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


def _headers(tenant_id: str) -> dict[str, str]:
    return {"x-api-key": "test-api-key", "x-tenant-id": tenant_id}


def _create_system(client: TestClient, tenant_id: str, system_id: str) -> None:
    payload = {
        "id": system_id,
        "name": "GM Test",
        "description": "Test",
        "business_unit": "BU",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": True,
        "criticality": AISystemCriticality.high.value,
        "data_sensitivity": DataSensitivity.internal.value,
        "has_incident_runbook": True,
        "has_supplier_risk_register": True,
        "has_backup_runbook": True,
    }
    r = client.post("/api/v1/ai-systems", json=payload, headers=_headers(tenant_id))
    assert r.status_code == 200, r.text


def test_governance_maturity_200_shape(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_READINESS_SCORE", "true")
    tid = f"gm-{uuid.uuid4().hex[:12]}"
    h = _headers(tid)
    _create_system(client, tid, "gm-sys-1")
    client.post(
        "/api/v1/ai-systems/gm-sys-1/runtime-events",
        headers=h,
        json={
            "events": [
                {
                    "source_event_id": "gm-hb",
                    "source": "sap_ai_core",
                    "event_type": "heartbeat",
                    "occurred_at": "2026-01-15T12:00:00+00:00",
                },
            ],
        },
    )
    r = client.get(f"/api/v1/tenants/{tid}/governance-maturity", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant_id"] == tid
    assert "governance_activity" in body
    assert 0 <= body["governance_activity"]["index"] <= 100
    assert body["governance_activity"]["level"] in ("low", "medium", "high")
    oam = body["operational_ai_monitoring"]
    assert oam["status"] in ("active", "not_configured")
    if oam["status"] == "active":
        assert oam["index"] is not None


def test_governance_maturity_forbidden_when_flag_off(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "false")
    tid = f"gm-{uuid.uuid4().hex[:12]}"
    r = client.get(f"/api/v1/tenants/{tid}/governance-maturity", headers=_headers(tid))
    assert r.status_code == 403
