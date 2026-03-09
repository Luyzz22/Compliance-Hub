import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers() -> dict[str, str]:
    os.environ["COMPLIANCEHUB_API_KEYS"] = "tenant-overview-key"
    return {
        "x-api-key": "tenant-overview-key",
        "x-tenant-id": "tenant-overview-001",
    }


def test_tenant_compliance_overview_aggregates_status_and_violations():
    systems = [
        {
            "id": "tenant-overview-compliant",
            "name": "Compliant System",
            "description": "No builtin violations",
            "business_unit": "Ops",
            "risk_level": "low",
            "ai_act_category": "minimal_risk",
            "gdpr_dpia_required": True,
            "owner_email": "owner@example.com",
            "criticality": "medium",
            "data_sensitivity": "internal",
        },
        {
            "id": "tenant-overview-non-compliant",
            "name": "Non-compliant System",
            "description": "Triggers high severity violation",
            "business_unit": "Risk",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": False,
            "owner_email": "risk-owner@example.com",
            "criticality": "medium",
            "data_sensitivity": "confidential",
        },
        {
            "id": "tenant-overview-partial",
            "name": "Partially compliant System",
            "description": "Triggers medium severity violation",
            "business_unit": "Finance",
            "risk_level": "low",
            "ai_act_category": "limited_risk",
            "gdpr_dpia_required": True,
            "owner_email": "",
            "criticality": "high",
            "data_sensitivity": "internal",
        },
    ]

    for payload in systems:
        response = client.post("/api/v1/ai-systems", json=payload, headers=_headers())
        assert response.status_code == 200

    overview_response = client.get("/api/v1/tenant/compliance-overview", headers=_headers())
    assert overview_response.status_code == 200

    overview = overview_response.json()

    assert overview["tenant_id"] == "tenant-overview-001"
    assert overview["total_systems"] == 3
    assert overview["compliant_systems"] == 1
    assert overview["partially_compliant_systems"] == 1
    assert overview["non_compliant_systems"] == 1

    assert overview["violations_by_rule"] == {
        "high-risk-without-dpia": 1,
        "high-criticality-without-owner": 1,
    }
    assert overview["violations_by_severity"] == {
        "high": 1,
        "medium": 1,
    }
    assert overview["last_evaluated_at"] is not None

