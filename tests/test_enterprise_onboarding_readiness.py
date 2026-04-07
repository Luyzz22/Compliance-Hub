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


def test_get_onboarding_readiness_baseline() -> None:
    tenant = "onboarding-readiness-tenant-a"
    resp = client.get("/api/internal/enterprise/onboarding-readiness", headers=_headers(tenant))
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == tenant
    assert "sso_readiness" in body
    assert "integration_readiness" in body


def test_put_onboarding_readiness_requires_manage_permission() -> None:
    tenant = "onboarding-readiness-tenant-b"
    payload = {
        "enterprise_name": "Test Holding",
        "advisor_visibility_enabled": True,
        "sso_readiness": {
            "provider_type": "azure_ad",
            "onboarding_status": "planned",
            "role_mapping_status": "planned",
            "identity_domain": "example.org",
            "metadata_hint": "enterprise rollout",
            "role_mapping_rules": [
                {"external_group_or_claim": "grp-chub-admins", "mapped_role": "tenant_admin"},
            ],
        },
        "integration_readiness": [
            {
                "target_type": "sap_btp",
                "readiness_status": "discovery",
                "owner": "integration@example.org",
                "notes": "BTP scope mapping",
                "blocker": "",
                "evidence_ref": "",
            }
        ],
    }
    denied = client.put(
        "/api/internal/enterprise/onboarding-readiness",
        headers=_headers(tenant, role="contributor"),
        json=payload,
    )
    assert denied.status_code == 403

    ok = client.put(
        "/api/internal/enterprise/onboarding-readiness",
        headers=_headers(tenant, role="tenant_admin"),
        json=payload,
    )
    assert ok.status_code == 200
    assert ok.json()["enterprise_name"] == "Test Holding"
