from __future__ import annotations

from pydantic import BaseModel, Field


class ProvisionTenantRequest(BaseModel):
    tenant_name: str = Field(..., min_length=1, max_length=255)
    industry: str = Field(..., min_length=1, max_length=128)
    country: str = Field(default="DE", max_length=64)
    nis2_scope: str = Field(default="in_scope", max_length=64)
    ai_act_scope: str = Field(default="in_scope", max_length=64)
    advisor_id: str | None = Field(default=None, max_length=255)
    enable_demo_seed: bool = False


class TenantApiKeyRead(BaseModel):
    id: str
    name: str
    key_last4: str
    created_at: str
    active: bool


class TenantApiKeyCreateBody(BaseModel):
    name: str = Field(default="API Key", min_length=1, max_length=255)


class TenantApiKeyCreated(BaseModel):
    id: str
    name: str
    key_last4: str
    created_at: str
    active: bool
    plain_key: str = Field(..., description="Einmalig bei Erstellung; sicher verwahren.")


class InitialProvisionedApiKey(BaseModel):
    key_id: str
    name: str
    key_last4: str
    plain_key: str


class ProvisionTenantResponse(BaseModel):
    tenant_id: str
    display_name: str
    industry: str
    country: str
    feature_flags: dict[str, bool]
    initial_api_key: InitialProvisionedApiKey
    advisor_linked: bool
    demo_seeded: bool = False
