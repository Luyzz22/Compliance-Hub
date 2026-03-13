import os

from fastapi.testclient import TestClient

from app.ai_system_models import AIActCategory, AISystemRiskLevel
from app.main import app

client = TestClient(app)


def _headers(tenant_id: str = "tenant-board-001") -> dict[str, str]:
    os.environ["COMPLIANCEHUB_API_KEYS"] = "test-api-key"
    return {"x-api-key": "test-api-key", "x-tenant-id": tenant_id}


def test_ai_board_kpis_endpoint_smoke() -> None:
    headers = _headers()

    create_resp = client.post(
        "/api/v1/ai-systems",
        headers=headers,
        json={
            "id": "board-ai-1",
            "name": "Board KPI System",
            "description": "System for board KPI smoke test",
            "business_unit": "Governance",
            "risk_level": AISystemRiskLevel.high.value,
            "ai_act_category": AIActCategory.high_risk.value,
            "gdpr_dpia_required": True,
            "owner_email": "board@example.com",
        },
    )
    assert create_resp.status_code == 200

    response = client.get("/api/v1/ai-governance/board-kpis", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "tenant-board-001"
    assert body["ai_systems_total"] >= 1
