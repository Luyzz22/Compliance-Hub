"""Tests für GET /api/v1/ai-governance/report/board/markdown."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _headers

client = TestClient(app)


def test_board_report_markdown_happy_path():
    """Markdown enthält Kapitelüberschriften und eingebettete Werte."""
    create = client.post(
        "/api/v1/ai-systems",
        json={
            "id": "md-report-sys",
            "name": "Markdown Report System",
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
        "/api/v1/ai-governance/report/board/markdown",
        headers=_headers(),
    )
    assert response.status_code == 200
    assert "text/markdown" in response.headers.get("content-type", "")
    assert "attachment" in response.headers.get("content-disposition", "").lower()
    text = response.text
    assert "# AI Governance Board Report" in text
    assert "## 1. Executive Summary" in text
    assert "## 2. KPIs" in text
    assert "## 3. Compliance-Readiness" in text
    assert "## 4. Incidents" in text
    assert "## 5. Supplier-Risiken" in text
    assert "## 6. Alerts" in text
    assert "board-kpi-tenant" in text


def test_board_report_markdown_tenant_isolation():
    """Anderer Tenant erhält eigenes Markdown (tenant_id im Inhalt)."""
    tenant_a = "md-tenant-a"
    tenant_b = "md-tenant-b"
    key = "board-kpi-key"
    for tid, sys_id in [(tenant_a, "mda-1"), (tenant_b, "mdb-1")]:
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
        "/api/v1/ai-governance/report/board/markdown",
        headers={"x-api-key": key, "x-tenant-id": tenant_a},
    )
    r_b = client.get(
        "/api/v1/ai-governance/report/board/markdown",
        headers={"x-api-key": key, "x-tenant-id": tenant_b},
    )
    assert r_a.status_code == 200 and r_b.status_code == 200
    assert tenant_a in r_a.text
    assert tenant_b in r_b.text


def test_board_report_markdown_401():
    """Ohne API-Key wird 401 zurückgegeben."""
    response = client.get(
        "/api/v1/ai-governance/report/board/markdown",
        headers={"x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401
