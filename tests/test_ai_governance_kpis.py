import os

from fastapi.testclient import TestClient

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    DataSensitivity,
)
from app.main import app

client = TestClient(app)


def _headers(tenant_id: str = "tenant-kpi-001") -> dict[str, str]:
    os.environ["COMPLIANCEHUB_API_KEYS"] = "test-api-key"
    return {
        "x-api-key": "test-api-key",
        "x-tenant-id": tenant_id,
    }


def test_ai_governance_kpis_endpoint_returns_expected_summary():
    headers = _headers("tenant-kpi-001")
    payloads = [
        {
            "id": "kpi-ai-1",
            "name": "High Risk Covered",
            "description": "High risk with controls",
            "business_unit": "Finance",
            "risk_level": AISystemRiskLevel.high.value,
            "ai_act_category": AIActCategory.high_risk.value,
            "gdpr_dpia_required": True,
            "owner_email": "owner1@example.com",
            "criticality": AISystemCriticality.high.value,
            "data_sensitivity": DataSensitivity.confidential.value,
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
        },
        {
            "id": "kpi-ai-2",
            "name": "High Risk Gap",
            "description": "High risk without dpia",
            "business_unit": "Operations",
            "risk_level": AISystemRiskLevel.high.value,
            "ai_act_category": AIActCategory.high_risk.value,
            "gdpr_dpia_required": False,
            "owner_email": "",
            "criticality": AISystemCriticality.high.value,
            "data_sensitivity": DataSensitivity.internal.value,
            "has_incident_runbook": False,
            "has_supplier_risk_register": False,
            "has_backup_runbook": False,
        },
    ]

    for payload in payloads:
        resp = client.post("/api/v1/ai-systems", json=payload, headers=headers)
        assert resp.status_code == 200

    response = client.get(
        "/api/v1/tenants/tenant-kpi-001/ai-governance-kpis",
        headers=headers,
    )
    assert response.status_code == 200

    body = response.json()
    assert body["tenant_id"] == "tenant-kpi-001"
    assert body["ai_systems_total"] == 2
    assert body["ai_systems_with_owner"] == 1
    assert body["high_risk_total"] == 2
    assert body["high_risk_with_dpia"] == 1
    assert body["policy_violations_open"] >= 1
    assert 0 <= body["governance_maturity_score"] <= 1


def test_ai_governance_kpis_forbidden_on_tenant_mismatch():
    headers = _headers("tenant-kpi-allowed")

    response = client.get(
        "/api/v1/tenants/tenant-kpi-other/ai-governance-kpis",
        headers=headers,
    )

    assert response.status_code == 403


def test_ai_governance_kpis_high_maturity_when_all_high_risk_have_dpia():
    headers = _headers("tenant-kpi-iso-42001")

    payload = {
        "id": "kpi-ai-iso-1",
        "name": "Mature High Risk",
        "description": "High risk fully covered",
        "business_unit": "Risk",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": True,
        "owner_email": "iso@example.com",
        "criticality": AISystemCriticality.high.value,
        "data_sensitivity": DataSensitivity.confidential.value,
        "has_incident_runbook": True,
        "has_supplier_risk_register": True,
        "has_backup_runbook": True,
    }

    create_resp = client.post("/api/v1/ai-systems", json=payload, headers=headers)
    assert create_resp.status_code == 200

    kpi_resp = client.get(
        "/api/v1/tenants/tenant-kpi-iso-42001/ai-governance-kpis",
        headers=headers,
    )
    assert kpi_resp.status_code == 200

    assert kpi_resp.json()["governance_maturity_score"] >= 0.8
