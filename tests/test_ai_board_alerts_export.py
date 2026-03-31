"""Tests für GET /api/v1/ai-governance/alerts/board/export (JSON/CSV)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _headers

client = TestClient(app)


def test_board_alerts_export_json_happy_path():
    """Export als JSON liefert AIKpiAlertExport mit tenant_id, generated_at, alerts."""
    create = client.post(
        "/api/v1/ai-systems",
        json={
            "id": "export-json-sys",
            "name": "Export Test",
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
        "/api/v1/ai-governance/alerts/board/export",
        params={"format": "json"},
        headers=_headers(),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers.get("content-disposition", "").lower()
    data = response.json()
    assert data["tenant_id"] == "board-kpi-tenant"
    assert "generated_at" in data
    assert data.get("format_version") == "1.0"
    assert isinstance(data["alerts"], list)
    for a in data["alerts"]:
        assert "id" in a and "kpi_key" in a and "severity" in a and "message" in a


def test_board_alerts_export_csv():
    """Export mit format=csv liefert text/csv, eine Zeile pro Alert."""
    response = client.get(
        "/api/v1/ai-governance/alerts/board/export",
        params={"format": "csv"},
        headers=_headers(),
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "").lower()
    text = response.text
    lines = text.strip().split("\n")
    assert len(lines) >= 1
    assert "id" in lines[0] and "kpi_key" in lines[0] and "severity" in lines[0]


def test_board_alerts_export_tenant_isolation():
    """Anderer Tenant erhält eigenen Export (tenant_id im Body/CSV)."""
    tenant_a = "export-tenant-a"
    tenant_b = "export-tenant-b"
    key = "board-kpi-key"
    for tid, sys_id in [(tenant_a, "ex-a-1"), (tenant_b, "ex-b-1")]:
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
        "/api/v1/ai-governance/alerts/board/export",
        params={"format": "json"},
        headers={"x-api-key": key, "x-tenant-id": tenant_a},
    )
    r_b = client.get(
        "/api/v1/ai-governance/alerts/board/export",
        params={"format": "json"},
        headers={"x-api-key": key, "x-tenant-id": tenant_b},
    )
    assert r_a.status_code == 200 and r_b.status_code == 200
    assert r_a.json()["tenant_id"] == tenant_a
    assert r_b.json()["tenant_id"] == tenant_b


def test_board_alerts_export_401():
    """Ohne API-Key wird 401 zurückgegeben."""
    response = client.get(
        "/api/v1/ai-governance/alerts/board/export",
        params={"format": "json"},
        headers={"x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401
