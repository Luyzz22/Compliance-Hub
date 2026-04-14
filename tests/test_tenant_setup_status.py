"""Tests für aggregierten Tenant-Guided-Setup-Status (Leselogik, Mandanten-Isolation)."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def _headers(tenant_id: str) -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
        "x-opa-user-role": "compliance_officer",
    }


def test_setup_status_empty_tenant() -> None:
    tid = "tenant-setup-empty-001"
    r = client.get(f"/api/v1/tenants/{tid}/setup-status", headers=_headers(tid))
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == tid
    assert body["ai_inventory_completed"] is False
    assert body["classification_completed"] is False
    assert body["classification_coverage_ratio"] == 0.0
    assert body["nis2_kpis_seeded"] is False
    assert body["policies_published"] is False
    assert body["actions_defined"] is False
    assert body["evidence_attached"] is False
    assert body["eu_ai_act_readiness_baseline_created"] is False
    assert body["completed_steps"] == 0
    assert body["total_steps"] == 7


def test_setup_status_forbidden_on_tenant_mismatch() -> None:
    r = client.get(
        "/api/v1/tenants/other-tenant/setup-status",
        headers=_headers("tenant-setup-allowed"),
    )
    assert r.status_code == 403


def test_setup_status_progresses_with_governance_data() -> None:
    tid = "tenant-setup-progress-001"
    h = _headers(tid)
    sid = "setup-progress-ai-1"

    s0 = client.get(f"/api/v1/tenants/{tid}/setup-status", headers=h).json()
    assert s0["completed_steps"] == 0

    pr = client.post(
        "/api/v1/ai-systems",
        headers=h,
        json={
            "id": sid,
            "name": "Setup Progress KI",
            "description": "Test",
            "business_unit": "IT",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "o@example.com",
            "criticality": "high",
            "data_sensitivity": "internal",
            "has_incident_runbook": False,
            "has_supplier_risk_register": False,
            "has_backup_runbook": False,
        },
    )
    assert pr.status_code == 200, pr.text

    s1 = client.get(f"/api/v1/tenants/{tid}/setup-status", headers=h).json()
    assert s1["ai_inventory_completed"] is True
    assert s1["policies_published"] is True
    assert s1["classification_completed"] is False
    assert s1["nis2_kpis_seeded"] is False
    assert 1 <= s1["completed_steps"] <= 3

    cl = client.post(
        f"/api/v1/ai-systems/{sid}/classify",
        headers=h,
        json={"use_case_domain": "critical_infra"},
    )
    assert cl.status_code == 200, cl.text

    s2 = client.get(f"/api/v1/tenants/{tid}/setup-status", headers=h).json()
    assert s2["classification_completed"] is True
    assert s2["nis2_kpis_seeded"] is False

    kr = client.post(
        f"/api/v1/ai-systems/{sid}/nis2-kritis-kpis",
        headers=h,
        json={"kpi_type": "INCIDENT_RESPONSE_MATURITY", "value_percent": 40},
    )
    assert kr.status_code == 200, kr.text

    s3 = client.get(f"/api/v1/tenants/{tid}/setup-status", headers=h).json()
    assert s3["nis2_kpis_seeded"] is True

    ar = client.post(
        "/api/v1/ai-governance/actions",
        headers=h,
        json={
            "related_ai_system_id": sid,
            "related_requirement": "EU AI Act Art. 9",
            "title": "Test-Massnahme",
            "status": "open",
        },
    )
    assert ar.status_code == 201, ar.text

    up = client.post(
        "/api/v1/evidence/uploads",
        headers=h,
        files={"file": ("e.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
        data={"ai_system_id": sid},
    )
    assert up.status_code == 201, up.text

    s4 = client.get(f"/api/v1/tenants/{tid}/setup-status", headers=h).json()
    assert s4["actions_defined"] is True
    assert s4["evidence_attached"] is True
    assert s4["eu_ai_act_readiness_baseline_created"] is False

    put = client.put(
        f"/api/v1/ai-systems/{sid}/compliance/art9_risk_management",
        headers=h,
        json={"status": "in_progress"},
    )
    assert put.status_code == 200, put.text

    s5 = client.get(f"/api/v1/tenants/{tid}/setup-status", headers=h).json()
    assert s5["eu_ai_act_readiness_baseline_created"] is True
    assert s5["completed_steps"] == 7
    for k in (
        "ai_inventory_completed",
        "classification_completed",
        "nis2_kpis_seeded",
        "policies_published",
        "actions_defined",
        "evidence_attached",
        "eu_ai_act_readiness_baseline_created",
    ):
        assert s5[k] is True, k


def test_setup_status_computation_isolated_between_tenants() -> None:
    """Tenant B bleibt leer, obwohl Tenant A Daten anlegt (gleicher Test-Client, frische IDs)."""
    ta = "tenant-setup-iso-a"
    tb = "tenant-setup-iso-b"
    sid = "setup-iso-ai"

    assert (
        client.post(
            "/api/v1/ai-systems",
            headers=_headers(ta),
            json={
                "id": sid,
                "name": "Iso A",
                "description": "x",
                "business_unit": "IT",
                "risk_level": "low",
                "ai_act_category": "minimal_risk",
                "gdpr_dpia_required": False,
                "owner_email": "a@example.com",
                "criticality": "low",
                "data_sensitivity": "internal",
                "has_incident_runbook": True,
                "has_supplier_risk_register": True,
                "has_backup_runbook": True,
            },
        ).status_code
        == 200
    )

    b_body = client.get(f"/api/v1/tenants/{tb}/setup-status", headers=_headers(tb)).json()
    assert b_body["ai_inventory_completed"] is False
    assert b_body["completed_steps"] == 0

    a_body = client.get(f"/api/v1/tenants/{ta}/setup-status", headers=_headers(ta)).json()
    assert a_body["ai_inventory_completed"] is True
