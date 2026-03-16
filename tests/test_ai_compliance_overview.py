"""Tests für GET /api/v1/ai-governance/compliance/overview (EU AI Act / ISO 42001 Board-Readiness)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers(tenant_id: str = "board-kpi-tenant", api_key: str = "board-kpi-key") -> dict[str, str]:
    return {"x-api-key": api_key, "x-tenant-id": tenant_id}


def test_compliance_overview_happy_path():
    """Happy Path: Overview liefert overall_readiness, Zähler, deadline, top_critical_requirements."""
    create = client.post(
        "/api/v1/ai-systems",
        json={
            "id": "overview-sys-1",
            "name": "KI-System für Overview",
            "description": "Test",
            "business_unit": "Ops",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": False,
            "owner_email": "a@b.de",
            "criticality": "medium",
            "data_sensitivity": "internal",
            "has_incident_runbook": False,
            "has_supplier_risk_register": False,
            "has_backup_runbook": False,
        },
        headers=_headers(),
    )
    assert create.status_code == 200

    response = client.get(
        "/api/v1/ai-governance/compliance/overview",
        headers=_headers(),
    )
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == "board-kpi-tenant"
    assert "overall_readiness" in data
    assert 0.0 <= data["overall_readiness"] <= 1.0
    assert "high_risk_systems_with_full_controls" in data
    assert "high_risk_systems_with_critical_gaps" in data
    assert "top_critical_requirements" in data
    assert isinstance(data["top_critical_requirements"], list)
    assert "deadline" in data
    assert data["deadline"] == "2026-08-02"
    assert "days_remaining" in data
    assert data["days_remaining"] >= 0


def test_compliance_overview_tenant_isolation():
    """Tenant A sieht nur eigene Aggregation; Tenant B hat eigene Zählwerte."""
    tenant_a = "overview-tenant-a"
    tenant_b = "overview-tenant-b"
    key = "board-kpi-key"

    for tid, sys_id in [(tenant_a, "overview-a-1"), (tenant_b, "overview-b-1")]:
        create = client.post(
            "/api/v1/ai-systems",
            json={
                "id": sys_id,
                "name": f"System {sys_id}",
                "description": "Test",
                "business_unit": "Ops",
                "risk_level": "high",
                "ai_act_category": "high_risk",
                "gdpr_dpia_required": False,
                "owner_email": "",
                "criticality": "medium",
                "data_sensitivity": "internal",
                "has_incident_runbook": False,
                "has_supplier_risk_register": False,
                "has_backup_runbook": False,
            },
            headers=_headers(tenant_id=tid, api_key=key),
        )
        assert create.status_code == 200

    resp_a = client.get(
        "/api/v1/ai-governance/compliance/overview",
        headers=_headers(tenant_id=tenant_a, api_key=key),
    )
    resp_b = client.get(
        "/api/v1/ai-governance/compliance/overview",
        headers=_headers(tenant_id=tenant_b, api_key=key),
    )
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    assert resp_a.json()["tenant_id"] == tenant_a
    assert resp_b.json()["tenant_id"] == tenant_b


def test_compliance_overview_401_without_api_key():
    """Ohne x-api-key wird 401 zurückgegeben."""
    response = client.get(
        "/api/v1/ai-governance/compliance/overview",
        headers={"x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401


def test_compliance_overview_401_invalid_api_key():
    """Mit ungültigem x-api-key wird 401 zurückgegeben."""
    response = client.get(
        "/api/v1/ai-governance/compliance/overview",
        headers={"x-api-key": "invalid-key", "x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401
