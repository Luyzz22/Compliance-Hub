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
    # Drei Systeme:
    # - 1x voll compliant (inkl. NIS2/ISO-Kontrollfelder)
    # - 2x klar non-compliant (High-Risk ohne DPIA, High Criticality ohne Owner)
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
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
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

    overview_response = client.get(
        "/api/v1/tenant/compliance-overview",
        headers=_headers(),
    )
    assert overview_response.status_code == 200

    overview = overview_response.json()

    assert overview["tenant_id"] == "tenant-overview-001"
    assert overview["total_systems"] == 3
    assert overview["compliant_systems"] == 1
    # Im aktuellen Policy-Setup werden beide übrigen Systeme als non-compliant gewertet.
    assert overview["partially_compliant_systems"] == 0
    assert overview["non_compliant_systems"] == 2

    assert overview["violations_by_rule"] == {
        "high-risk-without-dpia": 1,
        "high-criticality-without-owner": 1,
        "nis2-incident-runbook-missing": 2,
        "nis2-supplier-risk-register-missing": 2,
        "nis2-backup-recovery-missing": 2,
    }
    assert overview["violations_by_severity"] == {
        "high": 7,
        "medium": 1,
    }
    assert overview["last_evaluated_at"] is not None

