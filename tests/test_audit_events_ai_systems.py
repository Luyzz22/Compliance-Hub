import os

from fastapi.testclient import TestClient

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    AISystemStatus,
    DataSensitivity,
)
from app.main import app

client = TestClient(app)


def _headers(tenant_id: str) -> dict[str, str]:
    os.environ["COMPLIANCEHUB_API_KEYS"] = "test-api-key"
    return {
        "x-api-key": "test-api-key",
        "x-tenant-id": tenant_id,
    }


def _create_ai_system(tenant_id: str, system_id: str, *, with_violation: bool = False) -> None:
    payload = {
        "id": system_id,
        "name": f"System {system_id}",
        "description": "audit test system",
        "business_unit": "Risk",
        "risk_level": (
            AISystemRiskLevel.high.value
            if with_violation
            else AISystemRiskLevel.low.value
        ),
        "ai_act_category": (
            AIActCategory.high_risk.value
            if with_violation
            else AIActCategory.minimal_risk.value
        ),
        "gdpr_dpia_required": False if with_violation else True,
        "owner_email": "owner@example.com",
        "criticality": AISystemCriticality.medium.value,
        "data_sensitivity": DataSensitivity.internal.value,
    }
    response = client.post("/api/v1/ai-systems", json=payload, headers=_headers(tenant_id))
    assert response.status_code == 200


def test_audit_events_created_for_ai_system_lifecycle():
    tenant = "tenant-audit-lifecycle-1"
    ai_system_id = "ai-audit-lifecycle-1"

    _create_ai_system(tenant, ai_system_id)

    update_response = client.patch(
        f"/api/v1/ai-systems/{ai_system_id}",
        json={"description": "updated description"},
        headers=_headers(tenant),
    )
    assert update_response.status_code == 200

    status_response = client.patch(
        f"/api/v1/ai-systems/{ai_system_id}/status",
        params={"new_status": AISystemStatus.active.value},
        headers=_headers(tenant),
    )
    assert status_response.status_code == 200

    events_response = client.get(
        f"/api/v1/audit-events/ai-systems/{ai_system_id}",
        headers=_headers(tenant),
    )
    assert events_response.status_code == 200

    events = events_response.json()
    actions = {event["action"] for event in events}
    assert "created" in actions
    assert "updated" in actions
    assert "status_changed" in actions

    status_events = [event for event in events if event["action"] == "status_changed"]
    assert status_events
    assert status_events[0]["metadata"]["status"] == AISystemStatus.active.value


def test_audit_events_for_policy_evaluation():
    tenant = "tenant-audit-policy-1"
    ai_system_id = "ai-audit-policy-1"

    _create_ai_system(tenant, ai_system_id, with_violation=True)

    events_response = client.get("/api/v1/audit-events", headers=_headers(tenant))
    assert events_response.status_code == 200
    events = events_response.json()

    policy_events = [
        event
        for event in events
        if event["entity_type"] == "policy_evaluation"
        and event["entity_id"] == ai_system_id
        and event["action"] == "policies_evaluated"
    ]
    assert policy_events
    assert policy_events[0]["metadata"]["violations_count"] > 0


def test_audit_events_respect_tenant_isolation():
    tenant_a = "tenant-audit-isolation-a"
    tenant_b = "tenant-audit-isolation-b"

    _create_ai_system(tenant_a, "ai-audit-iso-a", with_violation=True)
    _create_ai_system(tenant_b, "ai-audit-iso-b", with_violation=True)

    events_a_response = client.get("/api/v1/audit-events", headers=_headers(tenant_a))
    assert events_a_response.status_code == 200
    events_a = events_a_response.json()

    assert events_a
    assert all(event["tenant_id"] == tenant_a for event in events_a)
    assert all(event["entity_id"] != "ai-audit-iso-b" for event in events_a)
