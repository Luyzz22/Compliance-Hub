"""Telemetrie demo_mutation_blocked bei 403 durch Demo-Schreibschutz."""

from __future__ import annotations

import json
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    DataSensitivity,
)
from app.db import SessionLocal
from app.main import app
from app.models_db import UsageEventTable
from app.repositories.tenant_registry import TenantRegistryRepository
from app.services import usage_event_logger

client = TestClient(app)


def _ai_payload(suffix: str) -> dict:
    return {
        "id": f"demo-tel-ai-{suffix}",
        "name": "Telemetry System",
        "description": "x",
        "business_unit": "IT",
        "risk_level": AISystemRiskLevel.low.value,
        "ai_act_category": AIActCategory.minimal_risk.value,
        "gdpr_dpia_required": False,
        "owner_email": "tel@example.com",
        "criticality": AISystemCriticality.low.value,
        "data_sensitivity": DataSensitivity.internal.value,
        "has_incident_runbook": True,
        "has_supplier_risk_register": True,
        "has_backup_runbook": True,
    }


def test_post_ai_system_emits_demo_mutation_blocked() -> None:
    tid = f"demo-mut-tel-{uuid.uuid4().hex[:10]}"
    s = SessionLocal()
    try:
        TenantRegistryRepository(s).create(
            tenant_id=tid,
            display_name="Mut Tel",
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
    before = SessionLocal()
    try:
        n0 = before.execute(
            select(UsageEventTable.id).where(
                UsageEventTable.tenant_id == tid,
                UsageEventTable.event_type == usage_event_logger.DEMO_MUTATION_BLOCKED,
            )
        ).all()
        n0_count = len(n0)
    finally:
        before.close()

    r = client.post("/api/v1/ai-systems", headers=h, json=_ai_payload(uuid.uuid4().hex[:8]))
    assert r.status_code == 403

    s2 = SessionLocal()
    try:
        rows = (
            s2.execute(
                select(UsageEventTable.payload_json).where(
                    UsageEventTable.tenant_id == tid,
                    UsageEventTable.event_type == usage_event_logger.DEMO_MUTATION_BLOCKED,
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == n0_count + 1
        payload = json.loads(rows[-1])
        assert payload["workspace_mode"] == "demo"
        assert payload["http_method"] == "POST"
        assert "/api/v1/ai-systems" in payload["route"]
    finally:
        s2.close()
