"""Workspace-Telemetrie: workspace_session_started und workspace_feature_used (GET)."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db import SessionLocal
from app.main import app
from app.models_db import UsageEventTable
from app.repositories.tenant_registry import TenantRegistryRepository
from app.services import usage_event_logger

client = TestClient(app)


def _count_usage(session, tenant_id: str, event_type: str) -> int:
    stmt = (
        select(func.count())
        .select_from(UsageEventTable)
        .where(
            UsageEventTable.tenant_id == tenant_id,
            UsageEventTable.event_type == event_type,
        )
    )
    return int(session.execute(stmt).scalar_one())


def _headers(tenant_id: str) -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tenant_id}


@pytest.fixture
def demo_tenant_id() -> str:
    tid = f"telemetry-demo-{uuid.uuid4().hex[:12]}"
    s = SessionLocal()
    try:
        TenantRegistryRepository(s).create(
            tenant_id=tid,
            display_name="Telemetry Demo",
            industry="IT",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=True,
            demo_playground=False,
        )
    finally:
        s.close()
    return tid


def test_tenant_meta_logs_demo_session_started_deduped(demo_tenant_id: str) -> None:
    r1 = client.get("/api/v1/workspace/tenant-meta", headers=_headers(demo_tenant_id))
    assert r1.status_code == 200, r1.text
    r2 = client.get("/api/v1/workspace/tenant-meta", headers=_headers(demo_tenant_id))
    assert r2.status_code == 200, r2.text

    s = SessionLocal()
    try:
        n = _count_usage(s, demo_tenant_id, usage_event_logger.DEMO_SESSION_STARTED)
        assert n == 1
        stmt = select(UsageEventTable.payload_json).where(
            UsageEventTable.tenant_id == demo_tenant_id,
            UsageEventTable.event_type == usage_event_logger.DEMO_SESSION_STARTED,
        )
        payload = json.loads(s.execute(stmt).scalars().first() or "{}")
        assert payload.get("event_type") == usage_event_logger.WORKSPACE_SESSION_STARTED
        assert payload.get("tenant_id") == demo_tenant_id
        assert payload.get("workspace_mode") == "demo"
        assert payload.get("actor_type") == "tenant"
        assert payload.get("result") == "success"
        assert payload.get("timestamp")
    finally:
        s.close()


def test_workspace_feature_used_inserts_event(demo_tenant_id: str) -> None:
    r = client.get(
        "/api/v1/workspace/feature-used",
        params={"feature_key": "board_ai_compliance_report"},
        headers=_headers(demo_tenant_id),
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True}

    s = SessionLocal()
    try:
        stmt = select(UsageEventTable.payload_json).where(
            UsageEventTable.tenant_id == demo_tenant_id,
            UsageEventTable.event_type == usage_event_logger.DEMO_FEATURE_USED,
        )
        rows = s.execute(stmt).scalars().all()
        assert len(rows) >= 1
        payload = json.loads(rows[-1])
        assert payload.get("event_type") == usage_event_logger.WORKSPACE_FEATURE_USED
        assert payload.get("tenant_id") == demo_tenant_id
        assert payload["feature_name"] == "board_ai_compliance_report"
        assert payload.get("workspace_mode") == "demo"
        assert payload.get("actor_type") == "tenant"
        assert payload.get("result") == "success"
        assert payload.get("timestamp")
    finally:
        s.close()


def test_demo_feature_used_404_when_not_demo() -> None:
    tid = f"non-demo-{uuid.uuid4().hex[:12]}"
    s = SessionLocal()
    try:
        TenantRegistryRepository(s).create(
            tenant_id=tid,
            display_name="Prod-like",
            industry="IT",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=False,
        )
    finally:
        s.close()

    r = client.get(
        "/api/v1/workspace/demo-feature-used",
        params={"feature_key": "wizard"},
        headers=_headers(tid),
    )
    assert r.status_code == 404
