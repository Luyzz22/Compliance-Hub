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


_original_get_settings_cache_clear = get_settings.cache_clear


def _clear_settings_cache() -> None:
    _original_get_settings_cache_clear()


get_settings.cache_clear = _clear_settings_cache  # type: ignore[attr-defined]


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
    if settings.api_keys and x_api_key not in settings.api_keys:
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
