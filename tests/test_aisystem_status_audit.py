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
        "x-tenant-id": "tenant-001",
        "x-opa-user-role": "contributor",
    }


def test_update_ai_system_status_creates_audit_log():
    # 1) AISystem anlegen
    create_payload = {
        "id": "ai-credit-scoring-v1",
        "name": "Credit Scoring Engine",
        "description": "Scores credit applications using machine learning.",
        "business_unit": "Risk Management",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": True,
        "owner_email": "owner@example.com",
        "criticality": AISystemCriticality.medium.value,
        "data_sensitivity": DataSensitivity.internal.value,
    }

    create_resp = client.post(
        "/api/v1/ai-systems",
        json=create_payload,
        headers=_headers(),
    )
    assert create_resp.status_code == 200

    # 2) Status aktualisieren
    update_resp = client.patch(
        "/api/v1/ai-systems/ai-credit-scoring-v1/status",
        params={"new_status": AISystemStatus.active.value},
        headers=_headers(),
    )
    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["status"] == AISystemStatus.active.value

    # 3) Audit-Logs prüfen
    audit_resp = client.get(
        "/api/v1/audit-logs",
        headers=_headers(),
    )
    assert audit_resp.status_code == 200
    logs = audit_resp.json()

    # Es sollte mindestens einen Eintrag mit der Status-Aktion geben
    actions = [log["action"] for log in logs]
    assert "update_ai_system_status" in actions

    status_logs = [log for log in logs if log["action"] == "update_ai_system_status"]
    assert status_logs, "Expected at least one status update audit log"

    log = status_logs[0]
    assert log["entity_type"] == "AISystem"
    assert log["entity_id"] == "ai-credit-scoring-v1"
    assert log["before"] is not None
    assert log["after"] is not None
