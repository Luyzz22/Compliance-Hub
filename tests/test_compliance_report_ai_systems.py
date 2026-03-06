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


def _headers() -> dict[str, str]:
    os.environ["COMPLIANCEHUB_API_KEYS"] = "test-api-key"
    return {
        "x-api-key": "test-api-key",
        "x-tenant-id": "tenant-report-001",
    }


def test_compliance_report_ai_systems_returns_aggregated_data():
    # Zwei AISysteme mit verschiedenen Risk Levels und Kategorien anlegen
    for idx, (risk, category) in enumerate(
        [
            (AISystemRiskLevel.high, AIActCategory.high_risk),
            (AISystemRiskLevel.limited, AIActCategory.limited_risk),
        ],
        start=1,
    ):
        payload = {
            "id": f"ai-system-{idx}",
            "name": f"System {idx}",
            "description": "Test AISystem for compliance report",
            "business_unit": "Risk Management",
            "risk_level": risk.value,
            "ai_act_category": category.value,
            "gdpr_dpia_required": True,
            "owner_email": f"owner{idx}@example.com",
            "criticality": AISystemCriticality.medium.value,
            "data_sensitivity": DataSensitivity.internal.value,
        }
        resp = client.post(
            "/api/v1/ai-systems",
            json=payload,
            headers=_headers(),
        )
        assert resp.status_code == 200

    # Report abrufen
    report_resp = client.get(
        "/api/v1/compliance/reports/ai-systems",
        headers=_headers(),
    )
    assert report_resp.status_code == 200

    report = report_resp.json()
    assert report["tenant_id"] == "tenant-report-001"
    assert report["total_systems"] == 2

    risk_levels = {item["risk_level"] for item in report["by_risk_level"]}
    assert AISystemRiskLevel.high.value in risk_levels
    assert AISystemRiskLevel.limited.value in risk_levels

    report = report_resp.json()
    assert report["tenant_id"] == "tenant-report-001"
    assert report["total_systems"] == 2

    risk_levels = {item["risk_level"] for item in report["by_risk_level"]}
    assert AISystemRiskLevel.high.value in risk_levels
    assert AISystemRiskLevel.limited.value in risk_levels

    criticalities = {item["criticality"] for item in report["by_criticality"]}
    assert AISystemCriticality.medium.value in criticalities

    sensitivities = {item["data_sensitivity"] for item in report["by_data_sensitivity"]}
    assert DataSensitivity.internal.value in sensitivities

