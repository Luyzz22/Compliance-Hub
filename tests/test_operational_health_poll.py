"""Operational resilience: internal poll + tenant governance read APIs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models_db import ServiceHealthIncidentTable, ServiceHealthSnapshotTable, TenantDB
from app.repositories.service_health import ServiceHealthRepository

client = TestClient(app)


@pytest.fixture()
def ops_tenant_id() -> str:
    tid = "operational-health-test-tenant"
    with Session(engine) as session:
        session.merge(
            TenantDB(
                id=tid,
                display_name="Operational Health Test",
                industry="software",
                country="DE",
            )
        )
        session.commit()
    yield tid
    with Session(engine) as session:
        session.query(ServiceHealthSnapshotTable).filter(
            ServiceHealthSnapshotTable.tenant_id == tid
        ).delete(synchronize_session=False)
        session.query(ServiceHealthIncidentTable).filter(
            ServiceHealthIncidentTable.tenant_id == tid
        ).delete(synchronize_session=False)
        session.query(TenantDB).filter(TenantDB.id == tid).delete(synchronize_session=False)
        session.commit()


@pytest.fixture()
def ops_tenant_polled(
    monkeypatch: pytest.MonkeyPatch,
    ops_tenant_id: str,
) -> str:
    """Tenant exists and at least one internal poll has written snapshots."""
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "poll-secret")
    monkeypatch.setenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "up")
    r = client.post(
        "/api/internal/health/poll/run",
        headers={"X-HEALTH-KEY": "poll-secret"},
    )
    assert r.status_code == 200
    return ops_tenant_id


def test_internal_poll_run_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "poll-secret")
    r = client.post("/api/internal/health/poll/run")
    assert r.status_code == 401


def test_internal_poll_run_writes_snapshots(
    monkeypatch: pytest.MonkeyPatch, ops_tenant_id: str
) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "poll-secret")
    monkeypatch.setenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "up")
    r = client.post(
        "/api/internal/health/poll/run",
        headers={"X-HEALTH-KEY": "poll-secret"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenants_processed"] >= 1
    assert body["snapshots_written"] >= 3

    with Session(engine) as session:
        repo = ServiceHealthRepository(session)
        rows = repo.list_snapshots(ops_tenant_id, limit=10)
        assert len(rows) >= 3
        assert {r.service_name for r in rows} >= {"app", "db", "external_ai_provider"}


def test_operations_snapshots_api(ops_tenant_polled: str) -> None:
    from tests.conftest import _headers

    h = _headers()
    h["x-tenant-id"] = ops_tenant_polled
    r = client.get("/api/v1/governance/operations/health/snapshots?limit=5", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


def test_operations_kpis_api(ops_tenant_polled: str) -> None:
    from tests.conftest import _headers

    h = _headers()
    h["x-tenant-id"] = ops_tenant_polled
    r = client.get("/api/v1/governance/operations/kpis", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "open_incidents" in data
    assert "degraded_services" in data


def test_patch_resolve_service_health_incident(ops_tenant_polled: str) -> None:
    from tests.conftest import _headers

    iid = str(uuid4())
    now = datetime.now(UTC)
    with Session(engine) as session:
        session.add(
            ServiceHealthIncidentTable(
                id=iid,
                tenant_id=ops_tenant_polled,
                service_name="app",
                previous_status="up",
                current_status="degraded",
                severity="warning",
                incident_state="open",
                source="internal_health_poll",
                detected_at=now,
                resolved_at=None,
                updated_at_utc=now,
                triggering_snapshot_id=None,
                title="Test-Incident",
                summary="pytest",
            )
        )
        session.commit()

    h = _headers()
    h["x-tenant-id"] = ops_tenant_polled
    r = client.patch(
        f"/api/v1/governance/operations/incidents/{iid}/resolve",
        headers=h,
        json={"resolved_note": "pytest manual"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["incident_state"] == "resolved"
    assert body["id"] == iid
