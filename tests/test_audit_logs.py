from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.security import get_settings


@pytest.fixture(autouse=True)
def _security_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("COMPLIANCEHUB_API_KEYS", "test-key-1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()




def test_audit_log_created_when_ai_system_created(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/ai-systems",
        headers={"x-api-key": "test-key-1", "x-tenant-id": "tenant-a"},
        json={
            "id": "ai-a-1",
            "name": "Fraud Model",
            "description": "Detects fraud",
            "business_unit": "Risk",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "owner@example.com",
        },
    )
    assert create_response.status_code == 200

    logs_response = client.get(
        "/api/v1/audit-logs",
        headers={"x-api-key": "test-key-1", "x-tenant-id": "tenant-a"},
    )

    assert logs_response.status_code == 200
    logs = logs_response.json()
    assert len(logs) >= 1
    assert any(log["action"] == "create_ai_system" and log["entity_id"] == "ai-a-1" for log in logs)


def test_audit_logs_are_tenant_isolated(client: TestClient) -> None:
    response_a = client.post(
        "/api/v1/ai-systems",
        headers={"x-api-key": "test-key-1", "x-tenant-id": "tenant-a"},
        json={
            "id": "ai-a-1",
            "name": "Model A",
            "description": "A",
            "business_unit": "Risk",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "owner@example.com",
        },
    )
    response_b = client.post(
        "/api/v1/ai-systems",
        headers={"x-api-key": "test-key-1", "x-tenant-id": "tenant-b"},
        json={
            "id": "ai-b-1",
            "name": "Model B",
            "description": "B",
            "business_unit": "Finance",
            "risk_level": "limited",
            "ai_act_category": "limited_risk",
            "gdpr_dpia_required": False,
            "owner_email": "owner@example.com",
        },
    )
    assert response_a.status_code == 200
    assert response_b.status_code == 200

    logs_tenant_a = client.get(
        "/api/v1/audit-logs",
        headers={"x-api-key": "test-key-1", "x-tenant-id": "tenant-a"},
    )
    assert logs_tenant_a.status_code == 200

    payload = logs_tenant_a.json()
    assert len(payload) >= 1
    assert all(log["tenant_id"] == "tenant-a" for log in payload)
    assert all(log["entity_id"] != "ai-b-1" for log in payload)
