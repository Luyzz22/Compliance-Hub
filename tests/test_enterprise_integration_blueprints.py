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


def test_get_integration_blueprints_returns_baseline() -> None:
    tenant = "integration-blueprint-tenant-a"
    resp = client.get(
        "/api/internal/enterprise/integration-blueprints?include_markdown=true",
        headers=_headers(tenant),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == tenant
    assert body["blueprint_rows"]
    assert "top_enterprise_integration_candidates" in body
    assert body["markdown_de"]


def test_put_integration_blueprint_requires_manage_permission() -> None:
    tenant = "integration-blueprint-tenant-b"
    payload = {
        "blueprint_id": "sap-s4-core",
        "source_system_type": "sap_s4hana",
        "evidence_domains": ["invoice", "approval", "access"],
        "onboarding_readiness_ref": "enterprise_onboarding_readiness",
        "security_prerequisites": ["SSO validiert", "Rollenmapping geprueft"],
        "data_owner": "finance-owner@example.org",
        "technical_owner": "it-owner@example.org",
        "integration_status": "designing",
        "blockers": [],
        "notes": "Mapping mit SAP FI/CO abstimmen.",
    }

    denied = client.put(
        "/api/internal/enterprise/integration-blueprints",
        headers=_headers(tenant, role="contributor"),
        json=payload,
    )
    assert denied.status_code == 403

    ok = client.put(
        "/api/internal/enterprise/integration-blueprints",
        headers=_headers(tenant, role="tenant_admin"),
        json=payload,
    )
    assert ok.status_code == 200
    body = ok.json()
    assert any(r["blueprint_id"] == "sap-s4-core" for r in body["blueprint_rows"])
