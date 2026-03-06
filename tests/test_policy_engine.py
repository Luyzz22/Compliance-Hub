from __future__ import annotations

import os
import uuid

from fastapi.testclient import TestClient

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    DataSensitivity,
)
from app.main import app
from app.security import get_settings

client = TestClient(app)


def _headers(tenant_id: str) -> dict[str, str]:
    os.environ["COMPLIANCEHUB_API_KEYS"] = "test-api-key"
    get_settings.cache_clear()
    return {
        "x-api-key": "test-api-key",
        "x-tenant-id": tenant_id,
    }


def test_create_high_risk_ai_system_creates_dpia_violation() -> None:
    tenant_id = f"tenant-policy-{uuid.uuid4()}"

    payload = {
        "id": f"ai-system-{uuid.uuid4()}",
        "name": "Credit Decisioning",
        "description": "High risk system",
        "business_unit": "Risk",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": False,
        "owner_email": "owner@example.com",
        "criticality": AISystemCriticality.medium.value,
        "data_sensitivity": DataSensitivity.internal.value,
    }

    create_resp = client.post("/api/v1/ai-systems", json=payload, headers=_headers(tenant_id))
    assert create_resp.status_code == 200

    violations_resp = client.get("/api/v1/violations", headers=_headers(tenant_id))
    assert violations_resp.status_code == 200
    violations = violations_resp.json()

    assert len(violations) >= 1
    assert any("requires gdpr_dpia_required=true" in item["message"] for item in violations)


def test_create_high_criticality_without_owner_email_creates_violation() -> None:
    tenant_id = f"tenant-policy-{uuid.uuid4()}"
    ai_system_id = f"ai-system-{uuid.uuid4()}"

    payload = {
        "id": ai_system_id,
        "name": "Ops Automation",
        "description": "Critical system",
        "business_unit": "Operations",
        "risk_level": AISystemRiskLevel.limited.value,
        "ai_act_category": AIActCategory.limited_risk.value,
        "gdpr_dpia_required": True,
        "owner_email": "",
        "criticality": AISystemCriticality.high.value,
        "data_sensitivity": DataSensitivity.confidential.value,
    }

    create_resp = client.post("/api/v1/ai-systems", json=payload, headers=_headers(tenant_id))
    assert create_resp.status_code == 200

    all_violations_resp = client.get("/api/v1/violations", headers=_headers(tenant_id))
    assert all_violations_resp.status_code == 200
    all_violations = all_violations_resp.json()
    assert any("requires a valid owner_email" in item["message"] for item in all_violations)

    per_system_resp = client.get(
        f"/api/v1/ai-systems/{ai_system_id}/violations",
        headers=_headers(tenant_id),
    )
    assert per_system_resp.status_code == 200
    per_system_violations = per_system_resp.json()

    assert len(per_system_violations) >= 1
    assert all(item["ai_system_id"] == ai_system_id for item in per_system_violations)
