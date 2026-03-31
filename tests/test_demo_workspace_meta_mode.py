"""Workspace-Meta: workspace_mode / Labels konsistent mit Schreibpolicy."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.repositories.tenant_registry import TenantRegistryRepository

client = TestClient(app)


def _headers(tenant_id: str) -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tenant_id}


def test_meta_mutation_blocked_matches_demo_readonly_tenant() -> None:
    tid = f"meta-ro-{uuid.uuid4().hex[:10]}"
    s = SessionLocal()
    try:
        TenantRegistryRepository(s).create(
            tenant_id=tid,
            display_name="Meta RO",
            industry="IT",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=True,
            demo_playground=False,
        )
    finally:
        s.close()

    r = client.get("/api/v1/workspace/tenant-meta", headers=_headers(tid))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mutation_blocked"] is True
    assert body["workspace_mode"] == "demo"
    assert body["is_demo"] is True


def test_meta_playground_not_mutation_blocked() -> None:
    tid = f"meta-pg-{uuid.uuid4().hex[:10]}"
    s = SessionLocal()
    try:
        TenantRegistryRepository(s).create(
            tenant_id=tid,
            display_name="Meta PG",
            industry="IT",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=True,
            demo_playground=True,
        )
    finally:
        s.close()

    r = client.get("/api/v1/workspace/tenant-meta", headers=_headers(tid))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mutation_blocked"] is False
    assert body["workspace_mode"] == "playground"


def test_meta_production_tenant() -> None:
    tid = f"meta-prod-{uuid.uuid4().hex[:10]}"
    s = SessionLocal()
    try:
        TenantRegistryRepository(s).create(
            tenant_id=tid,
            display_name="Meta Prod",
            industry="IT",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=False,
        )
    finally:
        s.close()

    r = client.get("/api/v1/workspace/tenant-meta", headers=_headers(tid))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mutation_blocked"] is False
    assert body["workspace_mode"] == "production"
    assert body["is_demo"] is False
