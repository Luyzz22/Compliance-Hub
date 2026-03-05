from __future__ import annotations

import os
from functools import lru_cache
from typing import Annotated

from fastapi import Header, HTTPException, status
from pydantic import BaseModel, Field


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
