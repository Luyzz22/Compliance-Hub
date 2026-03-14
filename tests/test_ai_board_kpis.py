from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _headers

client = TestClient(app)


def test_ai_board_kpis_endpoint_returns_summary():
    system_payload = {
        "id": "board-kpi-system-1",
        "name": "Board KPI System",
        "description": "System for board KPI smoke test",
        "business_unit": "Ops",
        "risk_level": "high",
        "ai_act_category": "high_risk",
        "gdpr_dpia_required": False,
        "owner_email": "",
        "criticality": "high",
        "data_sensitivity": "internal",
        "has_incident_runbook": False,
        "has_supplier_risk_register": False,
        "has_backup_runbook": False,
    }

    create_response = client.post(
        "/api/v1/ai-systems",
        json=system_payload,
        headers=_headers(),
    )
    assert create_response.status_code == 200

    response = client.get(
        "/api/v1/ai-governance/board-kpis",
        headers=_headers(),
    )
    assert response.status_code == 200

    data = response.json()
    assert data["tenant_id"] == "board-kpi-tenant"
    assert 0.0 <= data["board_maturity_score"] <= 1.0
    assert data["high_risk_systems_without_dpia"] >= 1
    assert data["critical_systems_without_owner"] >= 1
    assert data["nis2_control_gaps"] >= 1

