"""User / actor context passed into OPA action policies."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserPolicyContext(BaseModel):
    """Minimal actor context for policy evaluation (API-key auth today)."""

    tenant_id: str = Field(min_length=1)
    user_role: str = Field(
        min_length=1,
        description="Logical role for OPA: advisor, tenant_admin, tenant_user, viewer, …",
    )
