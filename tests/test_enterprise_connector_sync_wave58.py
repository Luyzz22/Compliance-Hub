from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models_db import EnterpriseConnectorInstanceDB

client = TestClient(app)


def _headers(tenant: str, role: str = "tenant_admin") -> dict[str, str]:
    return {
        "x-api-key": "test-key",
        "x-tenant-id": tenant,
        "x-opa-user-role": role,
    }


def test_connector_degraded_then_retry_succeeds() -> None:
    tenant = "connector-wave58-retry-tenant"
    client.get("/api/internal/enterprise/connector-runtime", headers=_headers(tenant))

    with Session(engine) as s:
        row = s.execute(
            select(EnterpriseConnectorInstanceDB).where(
                EnterpriseConnectorInstanceDB.tenant_id == tenant
            )
        ).scalar_one()
        row.connection_status = "degraded"
        s.commit()

    fail_resp = client.post(
        "/api/internal/enterprise/connector-runtime/manual-sync",
        headers=_headers(tenant),
    )
    assert fail_resp.status_code == 200
    fail_body = fail_resp.json()
    assert fail_body["sync_result"]["sync_status"] == "failed"
    assert fail_body["sync_result"]["failure_category"] == "source_unavailable"
    assert fail_body["sync_result"]["retry_recommended"] is True

    lf = client.get(
        "/api/internal/enterprise/connector-runtime/latest-failure",
        headers=_headers(tenant),
    )
    assert lf.status_code == 200
    assert lf.json()["sync_run_id"] == fail_body["sync_result"]["sync_run_id"]

    with Session(engine) as s:
        row = s.execute(
            select(EnterpriseConnectorInstanceDB).where(
                EnterpriseConnectorInstanceDB.tenant_id == tenant
            )
        ).scalar_one()
        row.connection_status = "connected"
        s.commit()

    retry_resp = client.post(
        "/api/internal/enterprise/connector-runtime/retry-sync",
        headers=_headers(tenant),
        json={},
    )
    assert retry_resp.status_code == 200
    retry_body = retry_resp.json()
    assert retry_body["sync_result"]["sync_status"] == "succeeded"
    assert (
        retry_body["sync_result"]["retry_of_sync_run_id"] == fail_body["sync_result"]["sync_run_id"]
    )


def test_connector_retry_sync_forbidden_for_viewer() -> None:
    tenant = "connector-wave58-viewer-tenant"
    r = client.post(
        "/api/internal/enterprise/connector-runtime/retry-sync",
        headers=_headers(tenant, role="viewer"),
        json={},
    )
    assert r.status_code == 403


def test_connector_retry_rejects_succeeded_run() -> None:
    tenant = "connector-wave58-succeeded-tenant"
    sync = client.post(
        "/api/internal/enterprise/connector-runtime/manual-sync",
        headers=_headers(tenant),
    )
    assert sync.status_code == 200
    run_id = sync.json()["sync_result"]["sync_run_id"]
    r = client.post(
        "/api/internal/enterprise/connector-runtime/retry-sync",
        headers=_headers(tenant),
        json={"sync_run_id": run_id},
    )
    assert r.status_code == 400
