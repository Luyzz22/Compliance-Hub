from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import _headers

client = TestClient(app)

# Separater Tenant für NIS2/ISO42001-Ratio-Tests, damit genau 2 Systeme gezählt werden
_NIS2_TENANT_HEADERS = {
    "x-api-key": "board-kpi-key",
    "x-tenant-id": "board-kpi-tenant-nis2",
}


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
    assert 0.0 <= data["nis2_incident_readiness_ratio"] <= 1.0
    assert 0.0 <= data["nis2_supplier_risk_coverage_ratio"] <= 1.0
    assert 0.0 <= data["iso42001_governance_score"] <= 1.0


def test_ai_board_kpis_nis2_and_iso42001_ratios_two_systems():
    """Zwei Systeme: eines voll ausgestattet (Runbooks + Supplier-Register), eines ohne Controls.
    Erwartung: nis2_incident_readiness_ratio = 0.5, nis2_supplier_risk_coverage_ratio = 0.5,
    iso42001_governance_score nachvollziehbar aus Owner/DPIA/Runbook/Supplier (beide 1/2)."""
    full_controls = {
        "id": "nis2-kpi-full",
        "name": "KI-System voll ausgestattet",
        "description": "Incident- und Backup-Runbook, Supplier-Register, Owner, DPIA",
        "business_unit": "Compliance",
        "risk_level": "high",
        "ai_act_category": "high_risk",
        "gdpr_dpia_required": True,
        "owner_email": "owner@example.com",
        "criticality": "medium",
        "data_sensitivity": "internal",
        "has_incident_runbook": True,
        "has_backup_runbook": True,
        "has_supplier_risk_register": True,
    }
    no_controls = {
        "id": "nis2-kpi-empty",
        "name": "KI-System ohne Controls",
        "description": "Keine Runbooks, kein Supplier-Register",
        "business_unit": "Ops",
        "risk_level": "high",
        "ai_act_category": "high_risk",
        "gdpr_dpia_required": False,
        "owner_email": "",
        "criticality": "medium",
        "data_sensitivity": "internal",
        "has_incident_runbook": False,
        "has_backup_runbook": False,
        "has_supplier_risk_register": False,
    }

    for payload in (full_controls, no_controls):
        create = client.post("/api/v1/ai-systems", json=payload, headers=_NIS2_TENANT_HEADERS)
        assert create.status_code == 200, create.text

    response = client.get("/api/v1/ai-governance/board-kpis", headers=_NIS2_TENANT_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert data["tenant_id"] == "board-kpi-tenant-nis2"
    assert data["ai_systems_total"] == 2

    # NIS2 Art. 21: nur 1 von 2 Systemen hat Incident- und Backup-Runbook
    assert data["nis2_incident_readiness_ratio"] == 0.5

    # NIS2 Art. 24: nur 1 von 2 Systemen hat Lieferanten-Risiko-Register
    assert data["nis2_supplier_risk_coverage_ratio"] == 0.5

    # ISO 42001: owner_ratio=0.5, dpia_ratio=0.5, runbook_ratio=0.5, supplier_ratio=0.5.
    # Das System ohne Controls erzeugt Policy-Violations (fehlende Runbooks/Supplier-Register),
    # violation_penalty = min(1, open_violations/2) = 1 → 0.15*(1 - 1) = 0 → Score = 0.425
    assert data["iso42001_governance_score"] == 0.425
