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


def test_authority_audit_pack_returns_structured_sections() -> None:
    tenant = "authority-pack-tenant-a"
    resp = client.get(
        "/api/internal/enterprise/authority-audit-pack?focus=mixed",
        headers=_headers(tenant),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == tenant
    assert body["focus"] == "mixed"
    assert "section_a_executive_posture" in body
    assert "section_f_recommended_next_preparation_actions" in body
    assert "markdown_de" in body
    assert body["source_sections"]


def test_authority_audit_pack_rejects_tenant_mismatch() -> None:
    tenant = "authority-pack-tenant-b"
    resp = client.get(
        "/api/internal/enterprise/authority-audit-pack?client_tenant_id=other-tenant",
        headers=_headers(tenant),
    )
    assert resp.status_code == 403
