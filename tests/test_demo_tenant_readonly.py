"""Demo-Mandanten: Schreibschutz für is_demo (optional demo_playground)."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    DataSensitivity,
)
from app.db import SessionLocal
from app.main import app
from app.repositories.tenant_registry import TenantRegistryRepository

client = TestClient(app)


def _ai_payload(suffix: str) -> dict:
    return {
        "id": f"demo-ro-ai-{suffix}",
        "name": "Demo RO System",
        "description": "x",
        "business_unit": "IT",
        "risk_level": AISystemRiskLevel.low.value,
        "ai_act_category": AIActCategory.minimal_risk.value,
        "gdpr_dpia_required": False,
        "owner_email": "ro@example.com",
        "criticality": AISystemCriticality.low.value,
        "data_sensitivity": DataSensitivity.internal.value,
        "has_incident_runbook": True,
        "has_supplier_risk_register": True,
        "has_backup_runbook": True,
    }


def test_demo_tenant_blocks_post_ai_system() -> None:
    tid = f"demo-ro-{uuid.uuid4().hex[:10]}"
    s = SessionLocal()
    try:
        TenantRegistryRepository(s).create(
            tenant_id=tid,
            display_name="RO Demo",
            industry="IT",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=True,
            demo_playground=False,
        )
    finally:
        s.close()

    h = {"x-api-key": "board-kpi-key", "x-tenant-id": tid}
    assert client.get("/api/v1/ai-systems", headers=h).status_code == 200

    r = client.post("/api/v1/ai-systems", headers=h, json=_ai_payload(uuid.uuid4().hex[:8]))
    assert r.status_code == 403
    assert "read-only" in r.json()["detail"].lower()


def test_demo_playground_allows_post_ai_system() -> None:
    tid = f"demo-pg-{uuid.uuid4().hex[:10]}"
    s = SessionLocal()
    try:
        TenantRegistryRepository(s).create(
            tenant_id=tid,
            display_name="PG Demo",
            industry="IT",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=True,
            demo_playground=True,
        )
    finally:
        s.close()

    suf = uuid.uuid4().hex[:8]
    h = {"x-api-key": "board-kpi-key", "x-tenant-id": tid}
    r = client.post("/api/v1/ai-systems", headers=h, json=_ai_payload(suf))
    assert r.status_code == 200, r.text
