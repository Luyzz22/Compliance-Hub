"""Tests für GET /api/v1/nis2-kritis/kpi-drilldown."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _headers

client = TestClient(app)


def _create_system(system_id: str) -> None:
    r = client.post(
        "/api/v1/ai-systems",
        json={
            "id": system_id,
            "name": system_id,
            "description": "Drilldown",
            "business_unit": "Ops",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "o@x.de",
            "criticality": "high",
            "data_sensitivity": "internal",
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
        },
        headers=_headers(),
    )
    assert r.status_code == 200, r.text


def test_nis2_kritis_drilldown_histogram_and_top_n():
    _create_system("dd-sys-a")
    _create_system("dd-sys-b")
    client.post(
        "/api/v1/ai-systems/dd-sys-a/nis2-kritis-kpis",
        headers=_headers(),
        json={"kpi_type": "INCIDENT_RESPONSE_MATURITY", "value_percent": 10},
    )
    client.post(
        "/api/v1/ai-systems/dd-sys-b/nis2-kritis-kpis",
        headers=_headers(),
        json={"kpi_type": "INCIDENT_RESPONSE_MATURITY", "value_percent": 80},
    )

    r = client.get(
        "/api/v1/nis2-kritis/kpi-drilldown",
        headers=_headers(),
        params={"top_n": 1},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == "board-kpi-tenant"
    assert data["top_n"] == 1
    assert len(data["by_kpi_type"]) == 3
    inc = next(x for x in data["by_kpi_type"] if x["kpi_type"] == "INCIDENT_RESPONSE_MATURITY")
    assert sum(b["count"] for b in inc["histogram"]) == 2
    assert inc["critical_systems"][0]["value_percent"] == 10
    assert inc["critical_systems"][0]["ai_system_id"] == "dd-sys-a"


def test_nis2_kritis_drilldown_tenant_isolation():
    tid_b = "drilldown-tenant-b-only"
    h_b = {"x-api-key": "board-kpi-key", "x-tenant-id": tid_b}
    tid_a = "drilldown-tenant-a-empty"
    h_a = {"x-api-key": "board-kpi-key", "x-tenant-id": tid_a}
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": "dd-b-1",
            "name": "X",
            "description": "d",
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
        headers=h_b,
    )
    client.post(
        "/api/v1/ai-systems/dd-b-1/nis2-kritis-kpis",
        headers=h_b,
        json={"kpi_type": "OT_IT_SEGREGATION", "value_percent": 40},
    )
    r_b = client.get("/api/v1/nis2-kritis/kpi-drilldown", headers=h_b)
    assert r_b.status_code == 200
    assert r_b.json()["tenant_id"] == tid_b
    ot_b = next(x for x in r_b.json()["by_kpi_type"] if x["kpi_type"] == "OT_IT_SEGREGATION")
    assert sum(b["count"] for b in ot_b["histogram"]) == 1

    r_a = client.get("/api/v1/nis2-kritis/kpi-drilldown", headers=h_a)
    assert r_a.status_code == 200
    ot_a = next(x for x in r_a.json()["by_kpi_type"] if x["kpi_type"] == "OT_IT_SEGREGATION")
    assert sum(b["count"] for b in ot_a["histogram"]) == 0
