"""Microsoft Entra OIDC verification and tenant-bound session creation.

Authorization never relies on mutable email or display-name claims. The immutable
``tid`` + ``oid`` pair must be pre-linked to a local user and tenant-specific role.
"""

from __future__ import annotations

import hmac
import json
import re
import uuid
from functools import lru_cache
from typing import Any, Protocol

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWTError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models_db import ExternalIdentityDB, IdentityProviderDB, UserDB
from app.repositories.user_sessions import UserSessionRepository
from app.repositories.users import UserRepository
from app.services.user_session_service import UserSessionService

_GUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_NIL_GUID = "00000000-0000-0000-0000-000000000000"
_ENTRA_ISSUER_RE = re.compile(
    r"^https://login\.microsoftonline\.com/"
    r"(?P<tenant>[0-9a-f-]{36})/v2\.0/?$",
    re.IGNORECASE,
)
_MAX_ID_TOKEN_BYTES = 24_000
_MAX_NONCE_BYTES = 256


class EntraTokenVerificationError(ValueError):
    """A token could not be proven to originate from the configured Entra tenant."""


class EntraTokenVerifierProtocol(Protocol):
    def verify(
        self,
        id_token: str,
        *,
        tenant_id: str,
        client_id: str,
        expected_nonce: str,
    ) -> dict[str, Any]: ...


def _normalized_guid(value: str, *, field: str) -> str:
    candidate = str(value or "").strip().lower()
    if not _GUID_RE.fullmatch(candidate) or candidate == _NIL_GUID:
        raise EntraTokenVerificationError(f"Invalid {field}")
    return candidate


def _entra_tenant_from_issuer(issuer_url: str | None) -> str:
    match = _ENTRA_ISSUER_RE.fullmatch(str(issuer_url or "").strip())
    if match is None:
        raise EntraTokenVerificationError(
            "Provider issuer is not a tenant-specific Entra v2 issuer"
        )
    return _normalized_guid(match.group("tenant"), field="provider tenant")


@lru_cache(maxsize=16)
def _jwks_client(tenant_id: str) -> PyJWKClient:
    return PyJWKClient(
        f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        cache_keys=True,
        lifespan=300,
        timeout=5,
    )


class EntraTokenVerifier:
    """Verify Entra ID tokens with a fixed algorithm, issuer and audience."""

    def verify(
        self,
        id_token: str,
        *,
        tenant_id: str,
        client_id: str,
        expected_nonce: str,
    ) -> dict[str, Any]:
        raw_token = str(id_token or "").strip()
        nonce = str(expected_nonce or "").strip()
        if not raw_token or len(raw_token.encode("utf-8")) > _MAX_ID_TOKEN_BYTES:
            raise EntraTokenVerificationError("Invalid ID token")
        if not nonce or len(nonce.encode("utf-8")) > _MAX_NONCE_BYTES:
            raise EntraTokenVerificationError("Invalid OIDC nonce")

        normalized_tenant = _normalized_guid(tenant_id, field="tenant ID")
        normalized_client = _normalized_guid(client_id, field="client ID")
        issuer = f"https://login.microsoftonline.com/{normalized_tenant}/v2.0"
        try:
            signing_key = _jwks_client(normalized_tenant).get_signing_key_from_jwt(raw_token)
            claims = jwt.decode(
                raw_token,
                signing_key,
                algorithms=["RS256"],
                audience=normalized_client,
                issuer=issuer,
                leeway=60,
                options={
                    "require": [
                        "aud",
                        "exp",
                        "iat",
                        "iss",
                        "nbf",
                        "nonce",
                        "oid",
                        "sub",
                        "tid",
                        "ver",
                    ]
                },
            )
        except (PyJWTError, OSError, TimeoutError, TypeError, ValueError) as exc:
            raise EntraTokenVerificationError("Entra ID token verification failed") from exc

        claim_tenant = _normalized_guid(str(claims.get("tid") or ""), field="tid claim")
        object_id = _normalized_guid(str(claims.get("oid") or ""), field="oid claim")
        if claim_tenant != normalized_tenant or str(claims.get("ver")) != "2.0":
            raise EntraTokenVerificationError("Unexpected Entra token tenant or version")
        token_nonce = str(claims.get("nonce") or "")
        if not hmac.compare_digest(token_nonce.encode("utf-8"), nonce.encode("utf-8")):
            raise EntraTokenVerificationError("OIDC nonce mismatch")

        roles = claims.get("roles", [])
        if roles is None:
            roles = []
        if not isinstance(roles, list) or any(
            not isinstance(role, str) or not role or len(role) > 128 for role in roles
        ):
            raise EntraTokenVerificationError("Invalid Entra app-role claims")
        claims["tid"] = claim_tenant
        claims["oid"] = object_id
        claims["roles"] = sorted(set(roles))
        return claims


def _provider_access_roles(provider: IdentityProviderDB) -> frozenset[str]:
    try:
        mapping = json.loads(provider.attribute_mapping or "{}")
    except json.JSONDecodeError as exc:
        raise EntraTokenVerificationError("Provider attribute mapping is invalid") from exc
    configured = mapping.get("required_app_roles")
    if isinstance(configured, str):
        configured = [configured]
    if not isinstance(configured, list):
        return frozenset()
    roles = {
        role.strip()
        for role in configured
        if isinstance(role, str) and role.strip() and len(role.strip()) <= 128
    }
    return frozenset(roles)


class EntraOIDCSessionService:
    """Map a verified Entra principal to a pre-provisioned local identity."""

    def __init__(
        self,
        session: Session,
        verifier: EntraTokenVerifierProtocol | None = None,
    ) -> None:
        self._session = session
        self._verifier = verifier or EntraTokenVerifier()

    def login(
        self,
        *,
        provider_id: str,
        id_token: str,
        expected_nonce: str,
    ) -> dict[str, Any]:
        provider = self._session.execute(
            select(IdentityProviderDB).where(
                IdentityProviderDB.id == str(provider_id).strip(),
                IdentityProviderDB.protocol == "oidc",
                IdentityProviderDB.enabled.is_(True),
            )
        ).scalar_one_or_none()
        if provider is None:
            return {"error": "provider_not_found", "detail": "OIDC provider not found or disabled"}

        try:
            tenant_id = _entra_tenant_from_issuer(provider.issuer_url)
            client_id = _normalized_guid(str(provider.client_id or ""), field="provider client ID")
            required_roles = _provider_access_roles(provider)
            if not required_roles:
                return {
                    "error": "provider_access_role_required",
                    "detail": "The Entra provider has no required application role",
                }
            claims = self._verifier.verify(
                id_token,
                tenant_id=tenant_id,
                client_id=client_id,
                expected_nonce=expected_nonce,
            )
        except EntraTokenVerificationError:
            return {
                "error": "invalid_identity_token",
                "detail": "Entra identity verification failed",
            }

        asserted_roles = frozenset(str(role) for role in claims.get("roles", []))
        if required_roles.isdisjoint(asserted_roles):
            return {
                "error": "required_app_role_missing",
                "detail": "The Entra principal is not assigned an approved application role",
            }

        external_subject = f"{claims['tid']}:{claims['oid']}"
        external_identity = self._session.execute(
            select(ExternalIdentityDB).where(
                ExternalIdentityDB.provider_id == provider.id,
                ExternalIdentityDB.external_subject == external_subject,
            )
        ).scalar_one_or_none()
        if external_identity is None:
            return {
                "error": "identity_not_provisioned",
                "detail": "The Entra principal is not provisioned for this tenant",
            }

        result = UserSessionService(
            UserRepository(self._session), UserSessionRepository(self._session)
        ).create_for_user(
            user_id=external_identity.user_id,
            tenant_id=provider.tenant_id,
            auth_method="entra_oidc",
        )
        if "error" in result:
            return result
        result["provider_id"] = provider.id
        return result


class EntraIdentityLinkService:
    """Explicit admin provisioning for immutable Entra principal links."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def link(
        self,
        *,
        local_tenant_id: str,
        provider_id: str,
        user_id: str,
        entra_tenant_id: str,
        entra_object_id: str,
    ) -> dict[str, Any]:
        provider = self._session.execute(
            select(IdentityProviderDB).where(
                IdentityProviderDB.id == provider_id,
                IdentityProviderDB.tenant_id == local_tenant_id,
                IdentityProviderDB.protocol == "oidc",
                IdentityProviderDB.enabled.is_(True),
            )
        ).scalar_one_or_none()
        if provider is None:
            return {"error": "provider_not_found", "detail": "OIDC provider not found or disabled"}
        try:
            configured_tenant = _entra_tenant_from_issuer(provider.issuer_url)
            asserted_tenant = _normalized_guid(entra_tenant_id, field="Entra tenant ID")
            object_id = _normalized_guid(entra_object_id, field="Entra object ID")
        except EntraTokenVerificationError:
            return {"error": "invalid_entra_identity", "detail": "Invalid Entra identity"}
        if configured_tenant != asserted_tenant:
            return {"error": "tenant_mismatch", "detail": "Entra tenant does not match provider"}

        user = self._session.execute(
            select(UserDB).where(UserDB.id == user_id)
        ).scalar_one_or_none()
        role = UserRepository(self._session).get_role(user_id, local_tenant_id)
        if user is None or role is None:
            return {
                "error": "local_membership_required",
                "detail": "User must already belong to the local tenant",
            }
        subject = f"{asserted_tenant}:{object_id}"
        existing_subject = self._session.execute(
            select(ExternalIdentityDB).where(
                ExternalIdentityDB.provider_id == provider.id,
                ExternalIdentityDB.external_subject == subject,
            )
        ).scalar_one_or_none()
        if existing_subject is not None:
            if existing_subject.user_id == user_id:
                return {
                    "id": existing_subject.id,
                    "provider_id": provider.id,
                    "user_id": user_id,
                    "external_subject": subject,
                    "created": False,
                }
            return {
                "error": "identity_already_linked",
                "detail": "Entra identity is already linked",
            }
        existing_user_link = self._session.execute(
            select(ExternalIdentityDB).where(
                ExternalIdentityDB.provider_id == provider.id,
                ExternalIdentityDB.user_id == user_id,
            )
        ).scalar_one_or_none()
        if existing_user_link is not None:
            return {
                "error": "user_already_linked",
                "detail": "User already has an identity for this provider",
            }

        row = ExternalIdentityDB(
            id=str(uuid.uuid4()),
            provider_id=provider.id,
            user_id=user_id,
            external_subject=subject,
            external_email=None,
            external_attributes=None,
        )
        self._session.add(row)
        try:
            self._session.commit()
        except IntegrityError:
            self._session.rollback()
            return {"error": "identity_link_conflict", "detail": "Identity link conflict"}
        return {
            "id": row.id,
            "provider_id": provider.id,
            "user_id": user_id,
            "external_subject": subject,
            "created": True,
        }
