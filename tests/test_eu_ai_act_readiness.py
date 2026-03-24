"""Tests für GET /api/v1/ai-governance/readiness/eu-ai-act."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _h(tid: str = "readiness-tenant-1") -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tid}


def test_eu_ai_act_readiness_happy_path():
    r = client.get(
        "/api/v1/ai-governance/readiness/eu-ai-act",
        headers=_h(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == "readiness-tenant-1"
    assert data["deadline"] == "2026-08-02"
    assert "days_remaining" in data
    assert 0.0 <= data["overall_readiness"] <= 1.0
    assert "high_risk_systems_essential_complete" in data
    assert "high_risk_systems_essential_incomplete" in data
    assert isinstance(data["critical_requirements"], list)
    assert isinstance(data["suggested_actions"], list)
    assert isinstance(data["open_governance_actions"], list)


def test_eu_ai_act_readiness_tenant_isolation():
    tid = "readiness-tenant-x"
    r = client.get("/api/v1/ai-governance/readiness/eu-ai-act", headers=_h(tid))
    assert r.status_code == 200
    assert r.json()["tenant_id"] == tid
