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


def _headers() -> dict[str, str]:
    os.environ["COMPLIANCEHUB_API_KEYS"] = "test-api-key"
    return {
        "x-api-key": "test-api-key",
        "x-tenant-id": "tenant-policy-001",
    }


def test_create_high_risk_without_dpia_creates_violation():
    payload = {
        "id": "ai-policy-risk-1",
        "name": "Policy Risk System",
        "description": "High risk no DPIA",
        "business_unit": "Risk",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": False,
        "owner_email": "owner@example.com",
        "criticality": AISystemCriticality.medium.value,
        "data_sensitivity": DataSensitivity.internal.value,
    }

    create_resp = client.post("/api/v1/ai-systems", json=payload, headers=_headers())
    assert create_resp.status_code == 200

    violations_resp = client.get("/api/v1/violations", headers=_headers())
    assert violations_resp.status_code == 200
    violations = violations_resp.json()

    matching = [
        item
        for item in violations
        if item["ai_system_id"] == "ai-policy-risk-1"
        and "DPIA" in item["message"]
    ]
    assert matching


def test_high_criticality_without_owner_email_creates_violation():
    payload = {
        "id": "ai-policy-criticality-1",
        "name": "Criticality System",
        "description": "High criticality no owner mail",
        "business_unit": "Ops",
        "risk_level": AISystemRiskLevel.limited.value,
        "ai_act_category": AIActCategory.limited_risk.value,
        "gdpr_dpia_required": True,
        "owner_email": "",
        "criticality": AISystemCriticality.high.value,
        "data_sensitivity": DataSensitivity.internal.value,
    }

    create_resp = client.post("/api/v1/ai-systems", json=payload, headers=_headers())
    assert create_resp.status_code == 200

    violations_resp = client.get(
        "/api/v1/ai-systems/ai-policy-criticality-1/violations",
        headers=_headers(),
    )
    assert violations_resp.status_code == 200

    violations = violations_resp.json()
    assert any("valid owner email" in item["message"] for item in violations)


def test_list_violations_filters_by_ai_system_and_is_idempotent_on_update():
    payload = {
        "id": "ai-policy-idempotent-1",
        "name": "Idempotent System",
        "description": "High risk no DPIA",
        "business_unit": "Risk",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": False,
        "owner_email": "owner@example.com",
        "criticality": AISystemCriticality.medium.value,
        "data_sensitivity": DataSensitivity.internal.value,
    }

    create_resp = client.post("/api/v1/ai-systems", json=payload, headers=_headers())
    assert create_resp.status_code == 200

    initial = client.get(
        "/api/v1/ai-systems/ai-policy-idempotent-1/violations",
        headers=_headers(),
    )
    assert initial.status_code == 200
    initial_count = len(initial.json())
    assert initial_count >= 1

    patch_resp = client.patch(
        "/api/v1/ai-systems/ai-policy-idempotent-1/status",
        params={"new_status": AISystemStatus.active.value},
        headers=_headers(),
    )
    assert patch_resp.status_code == 200

    after_update = client.get(
        "/api/v1/ai-systems/ai-policy-idempotent-1/violations",
        headers=_headers(),
    )
    assert after_update.status_code == 200
    assert len(after_update.json()) == initial_count

    unrelated_payload = {
        "id": "ai-policy-other-1",
        "name": "Other System",
        "description": "No violation expected",
        "business_unit": "Ops",
        "risk_level": AISystemRiskLevel.low.value,
        "ai_act_category": AIActCategory.minimal_risk.value,
        "gdpr_dpia_required": True,
        "owner_email": "other@example.com",
        "criticality": AISystemCriticality.low.value,
        "data_sensitivity": DataSensitivity.public.value,
    }
    other_create = client.post("/api/v1/ai-systems", json=unrelated_payload, headers=_headers())
    assert other_create.status_code == 200

    tenant_violations = client.get("/api/v1/violations", headers=_headers())
    assert tenant_violations.status_code == 200
    all_ids = {item["ai_system_id"] for item in tenant_violations.json()}
    assert "ai-policy-idempotent-1" in all_ids

    system_filtered = client.get(
        "/api/v1/ai-systems/ai-policy-other-1/violations",
        headers=_headers(),
    )
    assert system_filtered.status_code == 200
    assert system_filtered.json() == []
