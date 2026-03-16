"""Tests für Board-Report-Audit-Records (Audit-Ready, Versionierung, Export-Verknüpfung)."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.board_report_audit_records import _records
from app.services.board_report_export_jobs import _jobs
from tests.conftest import _headers

client = TestClient(app)


def _tenant_headers(tenant_id: str = "board-kpi-tenant") -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
    }


def setup_ai_system(
    tenant_id: str = "board-kpi-tenant",
    system_id: str | None = None,
) -> None:
    sid = system_id or "audit-test-sys"
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": sid,
            "name": "Audit Test",
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
        headers=_tenant_headers(tenant_id),
    )


def test_create_audit_record():
    """Erzeugen eines Audit-Records: 201, id, report_version, purpose."""
    _records.clear()
    setup_ai_system(system_id="audit-create-1")

    response = client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={
            "purpose": "NIS2 Board-Bericht",
            "status": "draft",
            "linked_export_job_ids": [],
        },
        headers=_headers(),
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["tenant_id"] == "board-kpi-tenant"
    assert data["purpose"] == "NIS2 Board-Bericht"
    assert data["status"] == "draft"
    assert data["report_version"] != ""
    assert data["linked_export_job_ids"] == []
    assert "report_generated_at" in data
    assert "created_by" in data


def test_audit_record_versioning():
    """Jeder Audit-Record erhält eine deterministische report_version (Hash über Report)."""
    _records.clear()
    setup_ai_system(system_id="audit-version-1")

    r1 = client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={"purpose": "EU AI Act High-Risk Audit", "status": "draft"},
        headers=_headers(),
    )
    r2 = client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={"purpose": "Zweiter Eintrag", "status": "final"},
        headers=_headers(),
    )
    assert r1.status_code == 201 and r2.status_code == 201
    v1, v2 = r1.json()["report_version"], r2.json()["report_version"]
    assert len(v1) == 16 and len(v2) == 16
    assert all(c in "0123456789abcdef" for c in v1 + v2)


def test_audit_record_tenant_isolation():
    """Audit-Record von Tenant A ist für Tenant B nicht sichtbar."""
    _records.clear()
    setup_ai_system("tenant-audit-a", system_id="audit-tenant-a")
    create = client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={"purpose": "Mandant A", "status": "draft"},
        headers=_tenant_headers("tenant-audit-a"),
    )
    assert create.status_code == 201
    audit_id = create.json()["id"]

    get_b = client.get(
        f"/api/v1/ai-governance/report/board/audit-records/{audit_id}",
        headers=_tenant_headers("tenant-audit-b"),
    )
    assert get_b.status_code == 404


def test_audit_record_linked_export_jobs():
    """Verknüpfung mit Export-Jobs: GET liefert linked_export_jobs."""
    _records.clear()
    _jobs.clear()
    setup_ai_system(system_id="audit-link-1")

    with patch(
        "app.services.board_report_export_jobs._post_with_headers",
        return_value=(True, ""),
    ):
        job_resp = client.post(
            "/api/v1/ai-governance/report/board/export-jobs",
            json={
                "target_system": "datev_dms_prepared",
                "callback_url": "https://x.com",
            },
            headers=_headers(),
        )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    create = client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={
            "purpose": "WP-Prüfungsdokumentation",
            "status": "final",
            "linked_export_job_ids": [job_id],
        },
        headers=_headers(),
    )
    assert create.status_code == 201
    audit_id = create.json()["id"]

    get_resp = client.get(
        f"/api/v1/ai-governance/report/board/audit-records/{audit_id}",
        headers=_headers(),
    )
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["linked_export_job_ids"] == [job_id]
    assert "linked_export_jobs" in data
    assert len(data["linked_export_jobs"]) == 1
    assert data["linked_export_jobs"][0]["id"] == job_id
    assert data["linked_export_jobs"][0]["target_system"] == "datev_dms_prepared"


def test_list_audit_records_paginated():
    """GET audit-records: Liste paginiert, Filter status."""
    _records.clear()
    setup_ai_system(system_id="audit-list-1")
    client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={"purpose": "Eins", "status": "draft"},
        headers=_headers(),
    )
    client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={"purpose": "Zwei", "status": "final"},
        headers=_headers(),
    )

    list_all = client.get(
        "/api/v1/ai-governance/report/board/audit-records?limit=10&offset=0",
        headers=_headers(),
    )
    assert list_all.status_code == 200
    items = list_all.json()
    assert len(items) >= 2

    list_draft = client.get(
        "/api/v1/ai-governance/report/board/audit-records?status=draft",
        headers=_headers(),
    )
    assert list_draft.status_code == 200
    drafts = list_draft.json()
    assert all(r["status"] == "draft" for r in drafts)


def test_audit_record_401_no_api_key():
    """POST ohne API-Key → 401."""
    response = client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={"purpose": "Test", "status": "draft"},
        headers={"x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401


def test_audit_record_401_invalid_api_key():
    """POST mit ungültigem API-Key → 401."""
    response = client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={"purpose": "Test", "status": "draft"},
        headers={"x-api-key": "invalid", "x-tenant-id": "board-kpi-tenant"},
    )
    assert response.status_code == 401
