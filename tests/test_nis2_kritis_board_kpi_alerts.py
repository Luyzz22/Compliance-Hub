"""Tests für NIS2-/KRITIS-KPI-basierte Board-Alerts."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_board_alert_nis2_incident_maturity_low_from_kpi_mean():
    """Niedriger Mittelwert INCIDENT_RESPONSE_MATURITY löst Alert aus."""
    tid = "alert-nis2-inc-tenant"
    h = {"x-api-key": "board-kpi-key", "x-tenant-id": tid}
    sid = "alert-nis2-inc-1"
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": sid,
            "name": sid,
            "description": "Test",
            "business_unit": "Ops",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "a@b.de",
            "criticality": "medium",
            "data_sensitivity": "internal",
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
        },
        headers=h,
    )
    client.post(
        f"/api/v1/ai-systems/{sid}/nis2-kritis-kpis",
        headers=h,
        json={"kpi_type": "INCIDENT_RESPONSE_MATURITY", "value_percent": 30},
    )
    r = client.get("/api/v1/ai-governance/alerts/board", headers=h)
    assert r.status_code == 200
    keys = {a["kpi_key"] for a in r.json()}
    assert "nis2_kritis_incident_maturity_low" in keys


def test_board_alert_nis2_ot_it_segmentation_risk():
    """Zwei Fokus-Systeme mit OT/IT < 60 % lösen kritischen Alert aus."""
    tid = "alert-nis2-ot-tenant"
    h = {"x-api-key": "board-kpi-key", "x-tenant-id": tid}
    for i, pct in enumerate((40, 45)):
        sid = f"alert-ot-{tid}-{i}"
        client.post(
            "/api/v1/ai-systems",
            json={
                "id": sid,
                "name": sid,
                "description": "OT Test",
                "business_unit": "Ops",
                "risk_level": "high",
                "ai_act_category": "high_risk",
                "gdpr_dpia_required": False,
                "owner_email": "",
                "criticality": "high",
                "data_sensitivity": "internal",
                "has_incident_runbook": True,
                "has_supplier_risk_register": True,
                "has_backup_runbook": True,
            },
            headers=h,
        )
        client.post(
            f"/api/v1/ai-systems/{sid}/nis2-kritis-kpis",
            headers=h,
            json={"kpi_type": "OT_IT_SEGREGATION", "value_percent": pct},
        )
    r = client.get("/api/v1/ai-governance/alerts/board", headers=h)
    assert r.status_code == 200
    keys = {a["kpi_key"] for a in r.json()}
    assert "nis2_kritis_ot_it_segmentation_risk" in keys


def test_board_alert_nis2_kpi_tenant_isolation():
    """NIS2-KPI-Alert-Daten sind tenant-isoliert."""
    tid = "alert-nis2-tenant-y"
    h = {"x-api-key": "board-kpi-key", "x-tenant-id": tid}
    sid = "alert-y-1"
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": sid,
            "name": sid,
            "description": "Test",
            "business_unit": "Ops",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "a@b.de",
            "criticality": "medium",
            "data_sensitivity": "internal",
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
        },
        headers=h,
    )
    client.post(
        f"/api/v1/ai-systems/{sid}/nis2-kritis-kpis",
        headers=h,
        json={"kpi_type": "INCIDENT_RESPONSE_MATURITY", "value_percent": 20},
    )
    r = client.get("/api/v1/ai-governance/alerts/board", headers=h)
    assert r.status_code == 200
    assert all(a["tenant_id"] == tid for a in r.json())
