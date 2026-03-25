from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

from fastapi import Header, HTTPException, status
from pydantic import BaseModel, Field


class AuthContext(BaseModel):
    tenant_id: str
    api_key: str


class SecuritySettings(BaseModel):
    api_keys: list[str] = Field(default_factory=list)

    @classmethod
    def from_env(cls) -> SecuritySettings:
        raw_keys = os.getenv("COMPLIANCEHUB_API_KEYS", "")
        keys = [key.strip() for key in raw_keys.split(",") if key.strip()]
        return cls(api_keys=keys)


@lru_cache
def get_settings() -> SecuritySettings:
    return SecuritySettings.from_env()


def validate_api_key_only(x_api_key: str | None) -> str:
    """Prüft nur den API-Key (ohne Tenant-Header), z. B. für Advisor-Portfolio."""
    if x_api_key is None or not x_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    settings = get_settings()
    if x_api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key.strip()


def advisor_id_allowlist() -> frozenset[str] | None:
    """
    Optional: COMPLIANCEHUB_ADVISOR_IDS=advisor-a@x.com,advisor-b@x.com
    Wenn gesetzt, dürfen nur diese advisor_ids Portfolio-Endpunkte nutzen.
    """
    raw = os.getenv("COMPLIANCEHUB_ADVISOR_IDS", "").strip()
    if not raw:
        return None
    ids = {part.strip() for part in raw.split(",") if part.strip()}
    return frozenset(ids) if ids else None


def require_advisor_api_access(
    advisor_id: str,
    x_advisor_id: Annotated[str | None, Header(alias="x-advisor-id")] = None,
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
) -> str:
    """
    Berater-Portfolio: gültiger API-Key, Pfad-advisor_id muss mit x-advisor-id übereinstimmen.
    """
    validate_api_key_only(x_api_key)
    if x_advisor_id is None or not str(x_advisor_id).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing x-advisor-id header",
        )
    if str(x_advisor_id).strip() != advisor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advisor ID mismatch with x-advisor-id header",
        )
    allowed = advisor_id_allowlist()
    if allowed is not None and advisor_id not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advisor not authorized for portfolio access",
        )
    return advisor_id


def get_api_key_and_tenant(
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="x-tenant-id")] = None,
) -> str:
    if x_tenant_id is None or not x_tenant_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing x-tenant-id header",
        )

    if x_api_key is None or not x_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    settings = get_settings()
    if x_api_key not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return x_tenant_id


def get_auth_context(
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="x-tenant-id")] = None,
) -> AuthContext:
    tenant_id = get_api_key_and_tenant(x_api_key=x_api_key, x_tenant_id=x_tenant_id)
    return AuthContext(tenant_id=tenant_id, api_key=x_api_key or "")


def delete_evidence_allowed_for_api_key(api_key: str) -> bool:
    """Nur API-Keys in COMPLIANCEHUB_EVIDENCE_DELETE_API_KEYS dürfen Evidence löschen."""
    raw = os.getenv("COMPLIANCEHUB_EVIDENCE_DELETE_API_KEYS", "")
    allowed = [k.strip() for k in raw.split(",") if k.strip()]
    if not allowed:
        return False
    return api_key in allowed
