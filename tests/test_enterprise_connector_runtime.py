from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers(tenant: str, role: str = "tenant_admin") -> dict[str, str]:
    return {
        "x-api-key": "test-key",
        "x-tenant-id": tenant,
        "x-opa-user-role": role,
    }


def test_connector_runtime_status_and_manual_sync() -> None:
    tenant = "connector-runtime-tenant-a"
    status_resp = client.get("/api/internal/enterprise/connector-runtime", headers=_headers(tenant))
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["connector_instance"]["source_system_type"] == "generic_api"
    assert status_body["connector_instance"]["enabled_evidence_domains"]

    sync_resp = client.post(
        "/api/internal/enterprise/connector-runtime/manual-sync",
        headers=_headers(tenant),
    )
    assert sync_resp.status_code == 200
    sync_body = sync_resp.json()
    assert sync_body["sync_result"]["sync_status"] == "success"
    assert sync_body["sync_result"]["records_ingested"] >= 1

    last_resp = client.get(
        "/api/internal/enterprise/connector-runtime/last-sync",
        headers=_headers(tenant),
    )
    assert last_resp.status_code == 200
    last_body = last_resp.json()
    assert last_body is not None
    assert last_body["sync_status"] == "success"
