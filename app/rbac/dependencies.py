"""FastAPI dependencies for enterprise RBAC permission checks."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Header, HTTPException, status

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


def _resolve_role(raw: str | None) -> EnterpriseRole:
    """Resolve a raw header value to an :class:`EnterpriseRole`.

    Returns :attr:`EnterpriseRole.CONTRIBUTOR` when *raw* is ``None``, empty,
    or not found in the legacy/new role map (case-insensitive lookup).
    """
    if raw is None or not raw.strip():
        return EnterpriseRole.CONTRIBUTOR  # safe default (tenant_user equivalent)
    key = raw.strip().lower()
    return _LEGACY_ROLE_MAP.get(key, EnterpriseRole.CONTRIBUTOR)


def require_permission(permission: Permission) -> Callable[..., EnterpriseRole]:
    """Return a FastAPI-compatible dependency that enforces *permission*."""

    def _check(
        x_opa_user_role: str | None = Header(None, alias="x-opa-user-role"),
    ) -> EnterpriseRole:
        role = _resolve_role(x_opa_user_role)
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return role

    return _check
