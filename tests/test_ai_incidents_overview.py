"""Tests für GET /api/v1/ai-governance/incidents/overview und /by-system (NIS2, ISO 42001)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models_db import IncidentTable

client = TestClient(app)

_INCIDENT_TENANT = "tenant-incident-overview"


def _create_incident(
    session: Session,
    tenant_id: str,
    ai_system_id: str,
    severity: str = "medium",
    status: str = "open",
) -> None:
    now = datetime.now(UTC)
    row = IncidentTable(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        ai_system_id=ai_system_id,
        severity=severity,
        status=status,
        created_at_utc=now - timedelta(days=1),
        updated_at_utc=now,
        acknowledged_at_utc=now if status != "open" else None,
        resolved_at_utc=now if status == "resolved" else None,
        actor="test",
        source="pytest",
        summary="Test incident",
    )
    session.add(row)
    session.commit()


def test_incidents_overview_happy_path():
    """Happy Path: Incidents für Tenant anlegen, Overview liefert Zählwerte und by_severity."""
    session = SessionLocal()
    try:
        # AI-System für by-system Namen
        create = client.post(
            "/api/v1/ai-systems",
            json={
                "id": "inc-sys-1",
                "name": "KI-System für Incidents",
                "description": "Test",
                "business_unit": "Ops",
                "risk_level": "high",
                "ai_act_category": "high_risk",
                "gdpr_dpia_required": False,
                "owner_email": "a@b.de",
                "criticality": "medium",
                "data_sensitivity": "internal",
                "has_incident_runbook": True,
                "has_supplier_risk_register": False,
                "has_backup_runbook": True,
            },
            headers={"x-api-key": "board-kpi-key", "x-tenant-id": _INCIDENT_TENANT},
        )
        assert create.status_code == 200

        _create_incident(session, _INCIDENT_TENANT, "inc-sys-1", "low", "open")
        _create_incident(session, _INCIDENT_TENANT, "inc-sys-1", "medium", "resolved")
        _create_incident(session, _INCIDENT_TENANT, "inc-sys-1", "high", "open")
    finally:
        session.close()

    response = client.get(
        "/api/v1/ai-governance/incidents/overview",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": _INCIDENT_TENANT},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == _INCIDENT_TENANT
    assert data["total_incidents_last_12_months"] == 3
    assert data["open_incidents"] == 2
    assert data["major_incidents_last_12_months"] == 1
    assert isinstance(data["by_severity"], list)
    assert len(data["by_severity"]) >= 1

    by_sys = client.get(
        "/api/v1/ai-governance/incidents/by-system",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": _INCIDENT_TENANT},
    )
    assert by_sys.status_code == 200
    list_by_sys = by_sys.json()
    assert isinstance(list_by_sys, list)
    assert len(list_by_sys) == 1
    assert list_by_sys[0]["ai_system_id"] == "inc-sys-1"
    assert list_by_sys[0]["ai_system_name"] == "KI-System für Incidents"
    assert list_by_sys[0]["incident_count"] == 3


def test_incidents_overview_tenant_isolation():
    """Tenant-Isolation: Incidents von Tenant B erscheinen nicht für Tenant A."""
    session = SessionLocal()
    try:
        _create_incident(session, "tenant-other-inc", "sys-other", "high", "open")
    finally:
        session.close()

    response = client.get(
        "/api/v1/ai-governance/incidents/overview",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": _INCIDENT_TENANT},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] == _INCIDENT_TENANT

    by_sys = client.get(
        "/api/v1/ai-governance/incidents/by-system",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": _INCIDENT_TENANT},
    )
    assert by_sys.status_code == 200
    list_by_sys = by_sys.json()
    system_ids = [e["ai_system_id"] for e in list_by_sys]
    assert "sys-other" not in system_ids


def test_incidents_overview_401_without_api_key():
    """Ohne gültigen API-Key liefert der Endpoint 401."""
    response = client.get(
        "/api/v1/ai-governance/incidents/overview",
        headers={"x-tenant-id": _INCIDENT_TENANT},
    )
    assert response.status_code == 401

    response2 = client.get(
        "/api/v1/ai-governance/incidents/overview",
        headers={"x-api-key": "invalid-key", "x-tenant-id": _INCIDENT_TENANT},
    )
    assert response2.status_code == 401
