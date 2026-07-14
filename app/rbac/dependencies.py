"""FastAPI dependencies for enterprise RBAC permission checks."""

from __future__ import annotations

import os
from collections.abc import Callable

from fastapi import Header, HTTPException, Request, status

from app.rbac.permissions import Permission, has_permission
from app.rbac.roles import EnterpriseRole

# Map legacy / OPA header role strings to EnterpriseRole values.
_LEGACY_ROLE_MAP: dict[str, EnterpriseRole] = {
    "advisor": EnterpriseRole.CONTRIBUTOR,
    "tenant_user": EnterpriseRole.CONTRIBUTOR,
    "viewer": EnterpriseRole.VIEWER,
    "auditor": EnterpriseRole.AUDITOR,
    "compliance_officer": EnterpriseRole.COMPLIANCE_OFFICER,
    "tenant_admin": EnterpriseRole.TENANT_ADMIN,
    # New roles map directly
    "contributor": EnterpriseRole.CONTRIBUTOR,
    "editor": EnterpriseRole.EDITOR,
    "ciso": EnterpriseRole.CISO,
    "board_member": EnterpriseRole.BOARD_MEMBER,
    "compliance_admin": EnterpriseRole.COMPLIANCE_ADMIN,
    "super_admin": EnterpriseRole.SUPER_ADMIN,
}


def resolve_enterprise_role(raw: str | None) -> EnterpriseRole:
    """Resolve a raw header value to an :class:`EnterpriseRole`.

    Unknown and absent roles resolve to the least-privileged viewer role.
    """
    if raw is None or not raw.strip():
        return EnterpriseRole.VIEWER
    key = raw.strip().lower()
    return _LEGACY_ROLE_MAP.get(key, EnterpriseRole.VIEWER)


def _resolve_role(raw: str | None) -> EnterpriseRole:
    """Backward-compatible alias for tests and integrations."""
    return resolve_enterprise_role(raw)


def _client_role_header_allowed() -> bool:
    raw = os.getenv("COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def require_permission(permission: Permission) -> Callable[..., EnterpriseRole]:
    """Return a FastAPI-compatible dependency that enforces *permission*."""

    def _check(
        request: Request,
        x_opa_user_role: str | None = Header(None, alias="x-opa-user-role"),
    ) -> EnterpriseRole:
        auth_context = getattr(request.state, "auth_context", None)
        session_role = getattr(auth_context, "role", None)
        if session_role:
            role = resolve_enterprise_role(session_role)
        elif _client_role_header_allowed():
            role = resolve_enterprise_role(x_opa_user_role)
        else:
            role = EnterpriseRole.VIEWER
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return role

    return _check
