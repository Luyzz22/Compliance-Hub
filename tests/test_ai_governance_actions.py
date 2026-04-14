"""Tests für CRUD /api/v1/ai-governance/actions."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _h(tid: str = "action-tenant-1") -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tid,
        "x-opa-user-role": "compliance_officer",
    }


def _create_system(sid: str, tid: str) -> None:
    r = client.post(
        "/api/v1/ai-systems",
        json={
            "id": sid,
            "name": sid,
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
        headers=_h(tid),
    )
    assert r.status_code == 200, r.text


def test_governance_actions_crud():
    tid = "action-crud-tenant"
    _create_system("act-sys-1", tid)
    h = _h(tid)
    c = client.post(
        "/api/v1/ai-governance/actions",
        headers=h,
        json={
            "related_ai_system_id": "act-sys-1",
            "related_requirement": "EU AI Act Art. 9",
            "title": "Risikomanagement dokumentieren",
            "status": "open",
        },
    )
    assert c.status_code == 201
    aid = c.json()["id"]
    assert c.json()["tenant_id"] == tid

    g = client.get(f"/api/v1/ai-governance/actions/{aid}", headers=h)
    assert g.status_code == 200

    u = client.patch(
        f"/api/v1/ai-governance/actions/{aid}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert u.status_code == 200
    assert u.json()["status"] == "in_progress"

    d = client.delete(f"/api/v1/ai-governance/actions/{aid}", headers=h)
    assert d.status_code == 204

    g404 = client.get(f"/api/v1/ai-governance/actions/{aid}", headers=h)
    assert g404.status_code == 404


def test_governance_action_invalid_system_404():
    r = client.post(
        "/api/v1/ai-governance/actions",
        headers=_h(),
        json={
            "related_ai_system_id": "does-not-exist",
            "related_requirement": "NIS2 Art. 21",
            "title": "x",
        },
    )
    assert r.status_code == 404


def test_governance_actions_tenant_isolation():
    tid1 = "ga-iso-1"
    tid2 = "ga-iso-2"
    _create_system("ga-s1", tid1)
    h1 = _h(tid1)
    h2 = _h(tid2)
    c = client.post(
        "/api/v1/ai-governance/actions",
        headers=h1,
        json={
            "related_ai_system_id": "ga-s1",
            "related_requirement": "ISO 42001",
            "title": "Nur Tenant 1",
        },
    )
    assert c.status_code == 201
    aid = c.json()["id"]
    assert client.get(f"/api/v1/ai-governance/actions/{aid}", headers=h2).status_code == 404
