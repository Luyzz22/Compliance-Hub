"""Tests für GET /api/v1/ai-governance/report/board/kpi-export und KPI-Export-Jobs."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.board_kpi_export_jobs import _jobs as _kpi_export_jobs_store
from tests.conftest import _headers

client = TestClient(app)


def test_board_kpi_export_json():
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": "kpi-exp-1",
            "name": "Export System",
            "description": "Produktion",
            "business_unit": "Fertigung",
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
    client.post(
        "/api/v1/ai-systems/kpi-exp-1/nis2-kritis-kpis",
        headers=_headers(),
        json={"kpi_type": "SUPPLIER_RISK_COVERAGE", "value_percent": 62},
    )
    r = client.get(
        "/api/v1/ai-governance/report/board/kpi-export",
        headers=_headers(),
        params={"format": "json"},
    )
    assert r.status_code == 200
    data = json.loads(r.text)
    assert data["format_version"] == "1.0"
    assert data["tenant_id"] == "board-kpi-tenant"
    row = next(s for s in data["systems"] if s["ai_system_id"] == "kpi-exp-1")
    assert row["nis2_kritis_supplier_risk_coverage_percent"] == 62
    assert row["high_risk_scenario_profile_id"] == "manufacturing_quality_control"


def test_board_kpi_export_csv():
    r = client.get(
        "/api/v1/ai-governance/report/board/kpi-export",
        headers=_headers(),
        params={"format": "csv"},
    )
    assert r.status_code == 200
    assert "tenant_id" in r.text
    assert "format_version" in r.text


def test_board_kpi_export_tenant_isolation():
    tid = "kpi-exp-tenant-z"
    h = {"x-api-key": "board-kpi-key", "x-tenant-id": tid}
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": "kpi-z-1",
            "name": "Z",
            "description": "d",
            "business_unit": "Ops",
            "risk_level": "low",
            "ai_act_category": "minimal_risk",
            "gdpr_dpia_required": False,
            "owner_email": "",
            "criticality": "low",
            "data_sensitivity": "internal",
            "has_incident_runbook": False,
            "has_supplier_risk_register": False,
            "has_backup_runbook": False,
        },
        headers=h,
    )
    r = client.get("/api/v1/ai-governance/report/board/kpi-export", headers=h)
    assert r.status_code == 200
    data = json.loads(r.text)
    assert len(data["systems"]) == 1
    assert data["systems"][0]["ai_system_id"] == "kpi-z-1"


def test_board_kpi_export_job_and_audit_link():
    _kpi_export_jobs_store.clear()
    job_r = client.post(
        "/api/v1/ai-governance/report/board/kpi-export/jobs",
        headers=_headers(),
        json={"target_system_label": "datev", "export_format": "json"},
    )
    assert job_r.status_code == 201
    job_id = job_r.json()["id"]

    from app.services.board_report_audit_records import _records

    _records.clear()
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": "audit-kpi-sys",
            "name": "A",
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
        headers=_headers(),
    )
    ar = client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        headers=_headers(),
        json={
            "purpose": "KPI-Export Nachweis",
            "status": "draft",
            "linked_kpi_export_job_ids": [job_id],
        },
    )
    assert ar.status_code == 201
    audit_id = ar.json()["id"]
    get_r = client.get(
        f"/api/v1/ai-governance/report/board/audit-records/{audit_id}",
        headers=_headers(),
    )
    assert get_r.status_code == 200
    body = get_r.json()
    assert job_id in body["linked_kpi_export_job_ids"]
    assert len(body["linked_kpi_export_jobs"]) == 1
    assert body["linked_kpi_export_jobs"][0]["id"] == job_id
