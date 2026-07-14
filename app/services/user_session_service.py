"""Application service for revocable, tenant-bound user sessions."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from app.rbac.dependencies import resolve_enterprise_role
from app.repositories.user_sessions import UserSessionRepository
from app.repositories.users import UserRepository
from app.services.identity_service import IdentityService


def _session_ttl() -> timedelta:
    raw = os.getenv("COMPLIANCEHUB_SESSION_TTL_MINUTES", "480")
    try:
        minutes = int(raw)
    except ValueError:
        minutes = 480
    return timedelta(minutes=max(5, min(minutes, 1_440)))


class UserSessionService:
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: UserSessionRepository,
    ) -> None:
        self._users = user_repo
        self._sessions = session_repo
        self._identity = IdentityService(user_repo)

    def login(
        self,
        *,
        email: str,
        password: str,
        tenant_id: str | None,
        auth_method: str = "password",
    ) -> dict:
        identity = self._identity.login(email=email, password=password)
        if "error" in identity:
            return identity
        if not identity.get("email_verified"):
            return {
                "error": "email_not_verified",
                "detail": "Email verification is required before starting a session",
            }

        assignments = identity.get("roles") or []
        requested_tenant = str(tenant_id or "").strip()
        selected = None
        if requested_tenant:
            selected = next(
                (item for item in assignments if item.get("tenant_id") == requested_tenant),
                None,
            )
            if selected is None:
                return {
                    "error": "tenant_access_denied",
                    "detail": "The user is not assigned to the requested tenant",
                }
        elif len(assignments) == 1:
            selected = assignments[0]
        elif len(assignments) > 1:
            return {
                "error": "tenant_selection_required",
                "detail": "Select a tenant before starting the session",
                "tenants": sorted(str(item["tenant_id"]) for item in assignments),
            }
        else:
            return {
                "error": "tenant_access_required",
                "detail": "No active tenant assignment is available",
            }

        role = resolve_enterprise_role(str(selected.get("role") or "viewer"))
        row, raw_token = self._sessions.create(
            user_id=str(identity["user_id"]),
            tenant_id=str(selected["tenant_id"]),
            role=role.value,
            auth_method=auth_method,
            ttl=_session_ttl(),
        )
        return {
            "session_token": raw_token,
            "session_id": row.id,
            "user_id": identity["user_id"],
            "email": identity["email"],
            "display_name": identity.get("display_name"),
            "tenant_id": row.tenant_id,
            "role": row.role,
            "auth_method": row.auth_method,
            "expires_at_utc": row.expires_at_utc.isoformat(),
        }

    def resolve(self, raw_token: str) -> dict | None:
        row = self._sessions.resolve(raw_token)
        if row is None:
            return None
        user = self._users.get_by_id(row.user_id)
        if user is None or not user.is_active or not user.email_verified:
            self._sessions.revoke(raw_token, reason="identity_inactive")
            return None
        assignment = self._users.get_role(row.user_id, row.tenant_id)
        if assignment is None:
            self._sessions.revoke(raw_token, reason="tenant_membership_removed")
            return None
        current_role = resolve_enterprise_role(assignment.role).value
        if current_role != row.role:
            self._sessions.revoke(raw_token, reason="role_changed")
            return None
        expires = row.expires_at_utc
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return {
            "session_id": row.id,
            "user_id": row.user_id,
            "email": user.email,
            "display_name": user.display_name,
            "tenant_id": row.tenant_id,
            "role": row.role,
            "auth_method": row.auth_method,
            "expires_at_utc": expires.astimezone(UTC).isoformat(),
            "resolved_at_utc": datetime.now(UTC).isoformat(),
        }

    def logout(self, raw_token: str) -> bool:
        return self._sessions.revoke(raw_token, reason="logout")
