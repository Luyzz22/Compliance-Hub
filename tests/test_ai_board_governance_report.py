"""Tests für GET /api/v1/ai-governance/report/board (Vorstands-/Aufsichtsreport)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _headers

client = TestClient(app)


def test_board_report_happy_path():
    """Response-Struktur und Feldbelegung (kpis, compliance, incidents, supplier, alerts)."""
    create = client.post(
        "/api/v1/ai-systems",
        json={
            "id": "report-sys-1",
            "name": "Report Test System",
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
        headers=_headers(),
    )
    assert create.status_code == 200

    response = client.get(
        "/api/v1/ai-governance/report/board",
        headers=_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == "board-kpi-tenant"
    assert "generated_at" in data
    assert data.get("period") == "last_12_months"
    assert "kpis" in data
    assert data["kpis"]["tenant_id"] == "board-kpi-tenant"
    assert "board_maturity_score" in data["kpis"]
    assert "compliance_overview" in data
    assert "overall_readiness" in data["compliance_overview"]
    assert "incidents_overview" in data
    assert "total_incidents_last_12_months" in data["incidents_overview"]
    assert "supplier_risk_overview" in data
    assert "total_systems_with_suppliers" in data["supplier_risk_overview"]
    assert "alerts" in data
    assert isinstance(data["alerts"], list)
    assert "operational_monitoring" in data


def test_board_report_tenant_isolation():
    """Anderer Tenant erhält eigenen Report (tenant_id in allen Teilstrukturen)."""
    tenant_a = "report-tenant-a"
    tenant_b = "report-tenant-b"
    key = "board-kpi-key"
    for tid, sys_id in [(tenant_a, "rpt-a-1"), (tenant_b, "rpt-b-1")]:
        client.post(
            "/api/v1/ai-systems",
            json={
                "id": sys_id,
                "name": sys_id,
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
            headers={"x-api-key": key, "x-tenant-id": tid},
        )

    r_a = client.get(
        "/api/v1/ai-governance/report/board",
        headers={"x-api-key": key, "x-tenant-id": tenant_a},
    )
    r_b = client.get(
        "/api/v1/ai-governance/report/board",
        headers={"x-api-key": key, "x-tenant-id": tenant_b},
    )
    assert r_a.status_code == 200 and r_b.status_code == 200
    assert r_a.json()["tenant_id"] == tenant_a
    assert r_b.json()["tenant_id"] == tenant_b
    assert r_a.json()["kpis"]["tenant_id"] == tenant_a
    assert r_b.json()["kpis"]["tenant_id"] == tenant_b


def test_board_report_401():
    """Ohne API-Key wird 401 zurückgegeben."""
    response = client.get(
        "/api/v1/ai-governance/report/board",
        headers={"x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401
