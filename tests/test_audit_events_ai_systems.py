import os

from fastapi.testclient import TestClient

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    AISystemStatus,
)
from app.main import app

client = TestClient(app)


def _headers(tenant_id: str) -> dict[str, str]:
    os.environ["COMPLIANCEHUB_API_KEYS"] = "test-api-key"
    return {
        "x-api-key": "test-api-key",
        "x-tenant-id": tenant_id,
    }


def _create_system(ai_system_id: str, tenant_id: str, *, gdpr_dpia_required: bool = True) -> None:
    payload = {
        "id": ai_system_id,
        "name": "Audit Trail System",
        "description": "System for audit event tests",
        "business_unit": "Risk",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": gdpr_dpia_required,
        "owner_email": "owner@example.com",
        "criticality": AISystemCriticality.medium.value,
        "data_sensitivity": "internal",
    }
    response = client.post("/api/v1/ai-systems", json=payload, headers=_headers(tenant_id))
    assert response.status_code == 200


def test_audit_events_created_for_ai_system_lifecycle():
    tenant_id = "tenant-audit-lifecycle"
    ai_system_id = "ai-audit-lifecycle-1"

    _create_system(ai_system_id, tenant_id)

    update_response = client.patch(
        f"/api/v1/ai-systems/{ai_system_id}",
        json={"description": "Updated by lifecycle test"},
        headers=_headers(tenant_id),
    )
    assert update_response.status_code == 200

    status_response = client.patch(
        f"/api/v1/ai-systems/{ai_system_id}/status",
        params={"new_status": AISystemStatus.active.value},
        headers=_headers(tenant_id),
    )
    assert status_response.status_code == 200

    events_response = client.get(
        f"/api/v1/audit-events/ai-systems/{ai_system_id}",
        headers=_headers(tenant_id),
    )
    assert events_response.status_code == 200
    events = events_response.json()

    actions = {item["action"] for item in events}
    assert "created" in actions
    assert "updated" in actions
    assert "status_changed" in actions

    status_changed = [item for item in events if item["action"] == "status_changed"]
    assert status_changed
    assert status_changed[0]["metadata"]["status"] == AISystemStatus.active.value


def test_audit_events_for_policy_evaluation():
    tenant_id = "tenant-audit-policy"
    ai_system_id = "ai-audit-policy-1"

    _create_system(ai_system_id, tenant_id, gdpr_dpia_required=False)

    response = client.get("/api/v1/audit-events", headers=_headers(tenant_id))
    assert response.status_code == 200
    events = response.json()

    policy_events = [event for event in events if event["entity_type"] == "policy_evaluation"]
    assert policy_events
    assert any((event["metadata"] or {}).get("violations_count", 0) > 0 for event in policy_events)


def test_audit_events_respect_tenant_isolation():
    tenant_a = "tenant-audit-a"
    tenant_b = "tenant-audit-b"

    _create_system("ai-audit-tenant-a-1", tenant_a)
    _create_system("ai-audit-tenant-b-1", tenant_b)

    events_a = client.get("/api/v1/audit-events", headers=_headers(tenant_a))
    events_b = client.get("/api/v1/audit-events", headers=_headers(tenant_b))

    assert events_a.status_code == 200
    assert events_b.status_code == 200

    payload_a = events_a.json()
    payload_b = events_b.json()

    assert payload_a
    assert payload_b
    assert all(event["tenant_id"] == tenant_a for event in payload_a)
    assert all(event["tenant_id"] == tenant_b for event in payload_b)
