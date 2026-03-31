"""Tests für GET /api/v1/ai-governance/readiness/eu-ai-act."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _h(tid: str = "readiness-tenant-1") -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tid}


def test_eu_ai_act_readiness_happy_path():
    r = client.get(
        "/api/v1/ai-governance/readiness/eu-ai-act",
        headers=_h(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == "readiness-tenant-1"
    assert data["deadline"] == "2026-08-02"
    assert "days_remaining" in data
    assert 0.0 <= data["overall_readiness"] <= 1.0
    assert "high_risk_systems_essential_complete" in data
    assert "high_risk_systems_essential_incomplete" in data
    assert isinstance(data["critical_requirements"], list)
    assert isinstance(data["suggested_actions"], list)
    assert isinstance(data["open_governance_actions"], list)


def test_eu_ai_act_readiness_tenant_isolation():
    tid = "readiness-tenant-x"
    r = client.get("/api/v1/ai-governance/readiness/eu-ai-act", headers=_h(tid))
    assert r.status_code == 200
    assert r.json()["tenant_id"] == tid


def test_eu_ai_act_readiness_critical_requirement_deep_links():
    """Kritische Anforderungen: System-IDs und verknüpfte Governance-Actions."""
    tid = "readiness-dl-tenant"
    h = _h(tid)
    sid = "readiness-dl-sys-1"
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": sid,
            "name": "DL High-Risk",
            "description": "Test",
            "business_unit": "Ops",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "a@b.de",
            "criticality": "high",
            "data_sensitivity": "internal",
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
        },
        headers=h,
    )
    cl = client.post(
        f"/api/v1/ai-systems/{sid}/classify",
        headers=h,
        json={"use_case_domain": "biometrics"},
    )
    assert cl.status_code == 200
    assert cl.json()["risk_level"] == "high_risk"
    action_r = client.post(
        "/api/v1/ai-governance/actions",
        headers=h,
        json={
            "related_ai_system_id": sid,
            "related_requirement": "EU AI Act Art. 9 – Risikomanagement",
            "title": "Risiko-Maßnahme testen",
            "status": "open",
        },
    )
    assert action_r.status_code == 201
    action_id = action_r.json()["id"]

    r = client.get("/api/v1/ai-governance/readiness/eu-ai-act", headers=h)
    assert r.status_code == 200
    data = r.json()
    art9 = next(
        (
            c
            for c in data["critical_requirements"]
            if c.get("requirement_id") == "art9_risk_management"
        ),
        None,
    )
    assert art9 is not None
    assert sid in (art9.get("related_ai_system_ids") or [])
    assert action_id in (art9.get("linked_governance_action_ids") or [])
    assert art9.get("open_actions_count_for_requirement", 0) >= 1
