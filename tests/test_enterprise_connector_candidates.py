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


def test_connector_candidates_returns_explainable_rows() -> None:
    tenant = "connector-candidates-tenant-a"
    resp = client.get(
        "/api/internal/enterprise/connector-candidates?include_markdown=true",
        headers=_headers(tenant),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == tenant
    assert body["candidate_rows"]
    assert "scoring_weights" in body
    assert "grouped_priorities_by_connector_type" in body
    assert body["markdown_de"]
