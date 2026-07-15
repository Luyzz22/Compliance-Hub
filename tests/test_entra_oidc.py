from __future__ import annotations

import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.main as main_module
from app.db import engine
from app.main import app
from app.repositories.users import UserRepository
from app.services.enterprise_iam_service import IdentityProviderService
from app.services.entra_oidc_service import (
    EntraIdentityLinkService,
    EntraOIDCSessionService,
    EntraTokenVerificationError,
    EntraTokenVerifier,
)
from app.services.identity_service import IdentityService
from tests.conftest import _headers

client = TestClient(app)
BFF_SECRET = "test-entra-bff-boundary-secret-at-least-32-bytes"
ACCESS_ROLE = "ComplianceHub.Access"


@pytest.fixture(autouse=True)
def _bff_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_BFF_SHARED_SECRET", BFF_SECRET)
    monkeypatch.setenv("COMPLIANCEHUB_ENTRA_ENABLED", "true")


class StaticVerifier:
    def __init__(self, *, tenant_id: str, object_id: str, roles: list[str] | None = None) -> None:
        self.tenant_id = tenant_id
        self.object_id = object_id
        self.roles = roles if roles is not None else [ACCESS_ROLE]

    def verify(
        self,
        id_token: str,
        *,
        tenant_id: str,
        client_id: str,
        expected_nonce: str,
    ) -> dict:
        assert id_token == "verified-id-token"
        assert tenant_id == self.tenant_id
        assert client_id
        assert expected_nonce == "n" * 48
        return {
            "tid": self.tenant_id,
            "oid": self.object_id,
            "roles": self.roles,
        }


def _provisioned_identity(*, local_tenant: str | None = None) -> dict[str, str]:
    local_tenant = local_tenant or f"entra-local-{uuid.uuid4()}"
    entra_tenant = str(uuid.uuid4())
    client_id = str(uuid.uuid4())
    object_id = str(uuid.uuid4())
    email = f"entra-{uuid.uuid4().hex}@example.com"
    with Session(engine) as session:
        identity = IdentityService(UserRepository(session))
        registered = identity.register(email=email, password="EnterprisePass123")
        verified = identity.verify_email(registered["verification_token"])
        identity.assign_role(verified["user_id"], local_tenant, "auditor", assigned_by="test")
        provider = IdentityProviderService(session).create_provider(
            tenant_id=local_tenant,
            slug=f"entra-{uuid.uuid4().hex}",
            display_name="Microsoft Entra ID",
            protocol="oidc",
            issuer_url=f"https://login.microsoftonline.com/{entra_tenant}/v2.0",
            client_id=client_id,
            attribute_mapping={"required_app_roles": [ACCESS_ROLE]},
        )
        linked = EntraIdentityLinkService(session).link(
            local_tenant_id=local_tenant,
            provider_id=provider["id"],
            user_id=verified["user_id"],
            entra_tenant_id=entra_tenant,
            entra_object_id=object_id,
        )
        assert linked["created"] is True
    return {
        "local_tenant": local_tenant,
        "entra_tenant": entra_tenant,
        "client_id": client_id,
        "object_id": object_id,
        "provider_id": provider["id"],
        "user_id": verified["user_id"],
    }


def test_entra_session_uses_preprovisioned_oid_and_local_role() -> None:
    provisioned = _provisioned_identity()
    with Session(engine) as session:
        result = EntraOIDCSessionService(
            session,
            StaticVerifier(
                tenant_id=provisioned["entra_tenant"],
                object_id=provisioned["object_id"],
            ),
        ).login(
            provider_id=provisioned["provider_id"],
            id_token="verified-id-token",
            expected_nonce="n" * 48,
        )
    assert "error" not in result
    assert result["user_id"] == provisioned["user_id"]
    assert result["tenant_id"] == provisioned["local_tenant"]
    assert result["role"] == "auditor"
    assert result["auth_method"] == "entra_oidc"
    assert result["session_token"].startswith("chs_")


def test_entra_session_rejects_unprovisioned_identity_and_missing_app_role() -> None:
    provisioned = _provisioned_identity()
    with Session(engine) as session:
        missing_role = EntraOIDCSessionService(
            session,
            StaticVerifier(
                tenant_id=provisioned["entra_tenant"],
                object_id=provisioned["object_id"],
                roles=["Unapproved.Role"],
            ),
        ).login(
            provider_id=provisioned["provider_id"],
            id_token="verified-id-token",
            expected_nonce="n" * 48,
        )
        unprovisioned = EntraOIDCSessionService(
            session,
            StaticVerifier(tenant_id=provisioned["entra_tenant"], object_id=str(uuid.uuid4())),
        ).login(
            provider_id=provisioned["provider_id"],
            id_token="verified-id-token",
            expected_nonce="n" * 48,
        )
    assert missing_role["error"] == "required_app_role_missing"
    assert unprovisioned["error"] == "identity_not_provisioned"


def test_entra_link_rejects_cross_tenant_or_email_only_linking() -> None:
    provisioned = _provisioned_identity()
    with Session(engine) as session:
        wrong_tenant = EntraIdentityLinkService(session).link(
            local_tenant_id=provisioned["local_tenant"],
            provider_id=provisioned["provider_id"],
            user_id=provisioned["user_id"],
            entra_tenant_id=str(uuid.uuid4()),
            entra_object_id=str(uuid.uuid4()),
        )
        duplicate_user = EntraIdentityLinkService(session).link(
            local_tenant_id=provisioned["local_tenant"],
            provider_id=provisioned["provider_id"],
            user_id=provisioned["user_id"],
            entra_tenant_id=provisioned["entra_tenant"],
            entra_object_id=str(uuid.uuid4()),
        )
    assert wrong_tenant["error"] == "tenant_mismatch"
    assert duplicate_user["error"] == "user_already_linked"


def test_entra_token_verifier_checks_signature_audience_issuer_and_nonce(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = str(uuid.uuid4())
    client_id = str(uuid.uuid4())
    object_id = str(uuid.uuid4())
    nonce = "nonce-value-with-at-least-32-characters"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = int(time.time())
    token = jwt.encode(
        {
            "aud": client_id,
            "exp": now + 300,
            "iat": now,
            "iss": f"https://login.microsoftonline.com/{tenant_id}/v2.0",
            "nbf": now - 1,
            "nonce": nonce,
            "oid": object_id,
            "roles": [ACCESS_ROLE],
            "sub": "pairwise-subject",
            "tid": tenant_id,
            "ver": "2.0",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "unit-test-key"},
    )
    public_jwk = jwt.PyJWK.from_dict(
        {
            **jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True),
            "kid": "unit-test-key",
        }
    )

    class StaticJwks:
        def get_signing_key_from_jwt(self, _token: str) -> jwt.PyJWK:
            return public_jwk

    monkeypatch.setattr("app.services.entra_oidc_service._jwks_client", lambda _: StaticJwks())
    claims = EntraTokenVerifier().verify(
        token,
        tenant_id=tenant_id,
        client_id=client_id,
        expected_nonce=nonce,
    )
    assert claims["oid"] == object_id
    with pytest.raises(EntraTokenVerificationError):
        EntraTokenVerifier().verify(
            token,
            tenant_id=tenant_id,
            client_id=client_id,
            expected_nonce="different-nonce-with-at-least-32-chars",
        )
    with pytest.raises(EntraTokenVerificationError):
        EntraTokenVerifier().verify(
            token,
            tenant_id=tenant_id,
            client_id=str(uuid.uuid4()),
            expected_nonce=nonce,
        )


def test_entra_session_api_requires_bff_and_never_uses_browser_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provisioned = _provisioned_identity(local_tenant="board-kpi-tenant")

    def verified_claims(
        _self: EntraTokenVerifier,
        _token: str,
        *,
        tenant_id: str,
        client_id: str,
        expected_nonce: str,
    ) -> dict:
        assert client_id == provisioned["client_id"]
        assert expected_nonce == "n" * 48
        return {
            "tid": tenant_id,
            "oid": provisioned["object_id"],
            "roles": [ACCESS_ROLE],
        }

    monkeypatch.setattr(EntraTokenVerifier, "verify", verified_claims)
    payload = {
        "provider_id": provisioned["provider_id"],
        "id_token": "x" * 100,
        "expected_nonce": "n" * 48,
        "role": "super_admin",
    }
    forbidden = client.post("/api/v1/auth/session/entra", json=payload)
    assert forbidden.status_code == 403

    response = client.post(
        "/api/v1/auth/session/entra",
        headers={"x-bff-secret": BFF_SECRET},
        json=payload,
    )
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "auditor"
    assert response.json()["auth_method"] == "entra_oidc"


def test_entra_session_api_requires_explicit_enablement_and_strong_bff_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "provider_id": str(uuid.uuid4()),
        "id_token": "x" * 100,
        "expected_nonce": "n" * 48,
    }
    monkeypatch.setenv("COMPLIANCEHUB_ENTRA_ENABLED", "false")
    disabled = client.post(
        "/api/v1/auth/session/entra",
        headers={"x-bff-secret": BFF_SECRET},
        json=payload,
    )
    assert disabled.status_code == 404

    monkeypatch.setenv("COMPLIANCEHUB_ENTRA_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_BFF_SHARED_SECRET", "short-bff-secret")
    weak_boundary = client.post(
        "/api/v1/auth/session/entra",
        headers={"x-bff-secret": "short-bff-secret"},
        json=payload,
    )
    assert weak_boundary.status_code == 503


def test_entra_link_api_requires_tenant_admin() -> None:
    provisioned = _provisioned_identity(local_tenant="board-kpi-tenant")
    response = client.post(
        f"/api/v1/enterprise/identity-providers/{provisioned['provider_id']}/entra-links",
        headers={**_headers(), "x-opa-user-role": "viewer"},
        json={
            "user_id": provisioned["user_id"],
            "entra_tenant_id": provisioned["entra_tenant"],
            "entra_object_id": provisioned["object_id"],
        },
    )
    assert response.status_code == 403


def test_legacy_attribute_callback_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMPLIANCEHUB_ALLOW_LEGACY_SSO_CALLBACK", raising=False)
    response = client.post(
        "/api/v1/enterprise/sso/callback",
        headers=_headers(),
        json={
            "provider_id": str(uuid.uuid4()),
            "external_subject": "unverified-subject",
            "external_email": "unverified@example.com",
        },
    )
    assert response.status_code == 410


def test_production_entra_disables_password_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main_module, "IS_PRODUCTION", True)
    monkeypatch.setenv("COMPLIANCEHUB_ENTRA_ENABLED", "true")
    response = client.post(
        "/api/v1/auth/session/login",
        headers={"x-bff-secret": BFF_SECRET},
        json={"email": "nobody@example.com", "password": "NotUsed123"},
    )
    assert response.status_code == 410
    assert response.json()["detail"]["code"] == "password_login_disabled"
