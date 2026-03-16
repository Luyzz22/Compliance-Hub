"""Tests für GET /api/v1/ai-governance/suppliers/overview und /by-system (NIS2 Art. 21/24)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_SUPPLIER_TENANT = "tenant-supplier-overview"


def test_suppliers_overview_happy_path():
    """Happy Path: KI-Systeme mit/ohne Supplier-Register, Overview und by-system."""
    headers = {"x-api-key": "board-kpi-key", "x-tenant-id": _SUPPLIER_TENANT}
    # System mit Register
    r1 = client.post(
        "/api/v1/ai-systems",
        json={
            "id": "sup-sys-1",
            "name": "KI-System mit Lieferanten-Register",
            "description": "Test",
            "business_unit": "Ops",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "a@b.de",
            "criticality": "high",
            "data_sensitivity": "internal",
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
        },
        headers=headers,
    )
    assert r1.status_code == 200
    # System ohne Register (kritisch)
    r2 = client.post(
        "/api/v1/ai-systems",
        json={
            "id": "sup-sys-2",
            "name": "Kritisches System ohne Register",
            "description": "Test",
            "business_unit": "Ops",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": False,
            "owner_email": "b@b.de",
            "criticality": "very_high",
            "data_sensitivity": "internal",
            "has_incident_runbook": False,
            "has_supplier_risk_register": False,
            "has_backup_runbook": False,
        },
        headers=headers,
    )
    assert r2.status_code == 200

    response = client.get(
        "/api/v1/ai-governance/suppliers/overview",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == _SUPPLIER_TENANT
    assert data["total_systems_with_suppliers"] == 1
    assert data["systems_without_supplier_risk_register"] == 1
    assert data["critical_suppliers_total"] == 2
    assert data["critical_suppliers_without_controls"] == 1
    assert "by_risk_level" in data
    assert len(data["by_risk_level"]) == 3

    by_sys = client.get(
        "/api/v1/ai-governance/suppliers/by-system",
        headers=headers,
    )
    assert by_sys.status_code == 200
    list_by_sys = by_sys.json()
    assert len(list_by_sys) == 2
    ids = {e["ai_system_id"] for e in list_by_sys}
    assert "sup-sys-1" in ids and "sup-sys-2" in ids
    entry_no_register = next(e for e in list_by_sys if e["ai_system_id"] == "sup-sys-2")
    assert entry_no_register["has_supplier_risk_register"] is False
    assert entry_no_register["supplier_risk_score"] == 1.0


def test_suppliers_overview_tenant_isolation():
    """Tenant-Isolation: Systeme von Tenant B erscheinen nicht für Tenant A."""
    other_headers = {"x-api-key": "board-kpi-key", "x-tenant-id": "tenant-other-supplier"}
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": "other-sup-1",
            "name": "Fremd-System",
            "description": "Test",
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
        },
        headers=other_headers,
    )

    response = client.get(
        "/api/v1/ai-governance/suppliers/overview",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": _SUPPLIER_TENANT},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == _SUPPLIER_TENANT
    assert data["total_systems_with_suppliers"] == 1

    by_sys = client.get(
        "/api/v1/ai-governance/suppliers/by-system",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": _SUPPLIER_TENANT},
    )
    assert by_sys.status_code == 200
    system_ids = [e["ai_system_id"] for e in by_sys.json()]
    assert "other-sup-1" not in system_ids


def test_suppliers_overview_401_without_api_key():
    """Ohne gültigen API-Key liefert der Endpoint 401."""
    response = client.get(
        "/api/v1/ai-governance/suppliers/overview",
        headers={"x-tenant-id": _SUPPLIER_TENANT},
    )
    assert response.status_code == 401

    response2 = client.get(
        "/api/v1/ai-governance/suppliers/overview",
        headers={"x-api-key": "invalid-key", "x-tenant-id": _SUPPLIER_TENANT},
    )
    assert response2.status_code == 401
