"""Tests für GET /api/v1/ai-governance/alerts/board (Board-KPI-Alerts)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_board_alerts_happy_path():
    """KPI-Kombinationen liefern erwartete Alerts (critical/warning bei niedrigen Ratios)."""
    tid = f"alerts-happy-{uuid.uuid4().hex[:10]}"
    h = {"x-api-key": "board-kpi-key", "x-tenant-id": tid}
    sys_id = f"alerts-sys-{uuid.uuid4().hex[:8]}"
    # System ohne Runbooks/Supplier-Register → niedrige NIS2-Ratios, niedriger ISO-Score
    payload = {
        "id": sys_id,
        "name": "System für Alerts-Test",
        "description": "Test",
        "business_unit": "Ops",
        "risk_level": "high",
        "ai_act_category": "high_risk",
        "gdpr_dpia_required": False,
        "owner_email": "",
        "criticality": "high",
        "data_sensitivity": "internal",
        "has_incident_runbook": False,
        "has_supplier_risk_register": False,
        "has_backup_runbook": False,
    }
    create = client.post("/api/v1/ai-systems", json=payload, headers=h)
    assert create.status_code == 200

    response = client.get(
        "/api/v1/ai-governance/alerts/board",
        headers=h,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    kpi_keys = {a["kpi_key"] for a in data}
    severities = {a["severity"] for a in data}
    for item in data:
        assert "id" in item
        assert item["tenant_id"] == tid
        assert item["kpi_key"]
        assert item["severity"] in ("info", "warning", "critical")
        assert item["message"]
        assert item["created_at"]
        assert item.get("resolved_at") is None
    # Bei schlechten KPIs erwarten wir mindestens einen critical/warning
    assert len(severities) >= 1
    expected_keys = {
        "nis2_incident_readiness_ratio",
        "iso42001_governance_score",
        "nis2_supplier_risk_coverage_ratio",
    }
    assert bool(kpi_keys & expected_keys)


def test_board_alerts_tenant_isolation():
    """Andere Tenant-Header liefern andere KPIs/Alerts (Tenant-Isolation)."""
    tenant_a = "alerts-tenant-a"
    tenant_b = "alerts-tenant-b"
    key = "board-kpi-key"
    for tid, sys_id in [(tenant_a, "alerts-a-1"), (tenant_b, "alerts-b-1")]:
        create = client.post(
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
        assert create.status_code == 200

    resp_a = client.get(
        "/api/v1/ai-governance/alerts/board",
        headers={"x-api-key": key, "x-tenant-id": tenant_a},
    )
    resp_b = client.get(
        "/api/v1/ai-governance/alerts/board",
        headers={"x-api-key": key, "x-tenant-id": tenant_b},
    )
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200
    list_a = resp_a.json()
    list_b = resp_b.json()
    assert all(a["tenant_id"] == tenant_a for a in list_a)
    assert all(b["tenant_id"] == tenant_b for b in list_b)


def test_board_alerts_401_without_api_key():
    """Ohne x-api-key wird 401 zurückgegeben."""
    response = client.get(
        "/api/v1/ai-governance/alerts/board",
        headers={"x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401


def test_board_alerts_401_invalid_api_key():
    """Mit ungültigem x-api-key wird 401 zurückgegeben."""
    response = client.get(
        "/api/v1/ai-governance/alerts/board",
        headers={"x-api-key": "invalid", "x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401
