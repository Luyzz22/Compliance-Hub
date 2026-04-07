from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _headers(
    tenant_id: str = "phase3-tenant",
    role: str = "tenant_admin",
) -> dict[str, str]:
    return {"x-api-key": "test-api-key", "x-tenant-id": tenant_id, "x-opa-user-role": role}


def _create_system(client: TestClient, tenant_id: str, system_id: str) -> None:
    payload = {
        "id": system_id,
        "name": f"System {system_id}",
        "description": "Phase3 test system",
        "business_unit": "Operations",
        "risk_level": "high",
        "ai_act_category": "high_risk",
        "gdpr_dpia_required": True,
    }
    resp = client.post("/api/v1/ai-systems", json=payload, headers=_headers(tenant_id))
    assert resp.status_code == 200, resp.text


def test_wizard_decision_and_inventory_mapping() -> None:
    client = TestClient(app)
    body = {
        "ai_system_id": "wiz-1",
        "questionnaire": {
            "use_case_domain": "employment",
            "is_narrow_procedural_task": True,
            "profiles_natural_persons": False,
        },
    }
    resp = client.post("/api/v1/ai-act/wizard/decision", json=body, headers=_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["decision_version"] == "eu_ai_act_v1"
    assert data["classification"]["risk_level"] in {
        "minimal_risk",
        "high_risk",
        "limited_risk",
        "prohibited",
    }
    assert "keine Rechtsberatung" in data["advisory_note_de"]
    assert "eu_ai_act_scope" in data["mapped_inventory_scope"]


def test_ki_register_versioning_and_authority_export() -> None:
    client = TestClient(app)
    tenant_id = "phase3-reg-tenant"
    system_id = "reg-sys-1"
    _create_system(client, tenant_id, system_id)

    profile_resp = client.put(
        f"/api/v1/ai-systems/{system_id}/inventory-profile",
        json={
            "provider_name": "Extern AI GmbH",
            "provider_type": "external",
            "use_case": "Bonitaetspruefung",
            "business_process": "credit_decision",
            "eu_ai_act_scope": "in_scope",
            "iso_42001_scope": "in_scope",
            "nis2_scope": "review_needed",
            "dsgvo_special_risk": "review_needed",
            "register_status": "planned",
            "register_metadata": {"operator": "banking_unit"},
            "authority_reporting_flags": {"reportable_incidents": True},
        },
        headers=_headers(tenant_id),
    )
    assert profile_resp.status_code == 200, profile_resp.text

    v1 = client.put(
        f"/api/v1/ki-register/entries/{system_id}",
        json={"status": "planned", "fields": {"stage": "initial"}},
        headers=_headers(tenant_id),
    )
    assert v1.status_code == 200
    assert v1.json()["version"] == 1

    v2 = client.put(
        f"/api/v1/ki-register/entries/{system_id}",
        json={
            "status": "registered",
            "authority_name": "Landesaufsicht",
            "national_register_id": "DE-KI-12345",
            "reportable_incident": True,
            "fields": {"stage": "update"},
        },
        headers=_headers(tenant_id),
    )
    assert v2.status_code == 200
    assert v2.json()["version"] == 2

    posture = client.get("/api/v1/ki-register/posture", headers=_headers(tenant_id))
    assert posture.status_code == 200
    assert posture.json()["registered"] == 1

    export_resp = client.get(
        "/api/v1/authority/ai-act/export?scope=incident_context",
        headers=_headers(tenant_id, role="auditor"),
    )
    assert export_resp.status_code == 200, export_resp.text
    payload = export_resp.json()
    assert payload["export"]["scope"] == "incident_context"
    assert len(payload["export"]["systems"]) == 1
    assert "keine Rechtsberatung" in payload["markdown_de"]


def test_ki_register_rbac_enforced() -> None:
    client = TestClient(app)
    tenant_id = "phase3-rbac-tenant"
    system_id = "rbac-sys-1"
    _create_system(client, tenant_id, system_id)
    denied = client.put(
        f"/api/v1/ki-register/entries/{system_id}",
        json={"status": "planned"},
        headers=_headers(tenant_id, role="viewer"),
    )
    assert denied.status_code == 403
