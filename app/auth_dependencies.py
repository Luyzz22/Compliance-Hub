"""FastAPI-Dependencies: Mandanten-Auth mit globalem Key-Pool (ENV) und tenant_api_keys (DB)."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.demo_tenant_guard import ensure_tenant_writes_allowed_if_not_demo
from app.repositories.tenant_api_keys import TenantApiKeyRepository
from app.repositories.user_sessions import UserSessionRepository
from app.repositories.users import UserRepository
from app.security import AuthContext, get_settings, secret_matches_any
from app.services.user_session_service import UserSessionService


def _global_api_keys_allowed() -> bool:
    environment = os.getenv("COMPLIANCEHUB_ENV", "dev").strip().lower()
    if environment not in {"prod", "production"}:
        return True
    raw = os.getenv("COMPLIANCEHUB_ALLOW_GLOBAL_API_KEYS", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def resolve_tenant_id_for_api_key(
    session: Session,
    x_api_key: str | None,
    x_tenant_id: str | None,
) -> tuple[str, str]:
    """
    Gibt (tenant_id, api_key) zurück.
    Zuerst COMPLIANCEHUB_API_KEYS (bestehendes Verhalten), sonst aktiver DB-Key für den Mandanten.
    """
    if x_tenant_id is None or not str(x_tenant_id).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing x-tenant-id header",
        )
    tenant_id = str(x_tenant_id).strip()

    if x_api_key is None or not str(x_api_key).strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )
    api_key = str(x_api_key).strip()

    settings = get_settings()
    if _global_api_keys_allowed() and secret_matches_any(api_key, settings.api_keys):
        return tenant_id, api_key

    repo = TenantApiKeyRepository(session)
    if repo.verify_key(tenant_id=tenant_id, raw_key=api_key):
        return tenant_id, api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def _bearer_token(authorization: str | None) -> str | None:
    if authorization is None or not authorization.strip():
        return None
    scheme, separator, value = authorization.strip().partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
        )
    return value.strip()


def _resolve_request_auth_context(
    *,
    request: Request,
    session: Session,
    x_api_key: str | None,
    x_tenant_id: str | None,
    authorization: str | None,
) -> AuthContext:
    cached = getattr(request.state, "auth_context", None)
    if isinstance(cached, AuthContext):
        return cached

    bearer = _bearer_token(authorization)
    if bearer and x_api_key and x_api_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ambiguous credentials",
        )

    if bearer:
        principal = UserSessionService(
            UserRepository(session), UserSessionRepository(session)
        ).resolve(bearer)
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session",
            )
        requested_tenant = str(x_tenant_id or "").strip()
        if requested_tenant and requested_tenant != principal["tenant_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session tenant does not match x-tenant-id",
            )
        context = AuthContext(
            tenant_id=principal["tenant_id"],
            user_id=principal["user_id"],
            role=principal["role"],
            session_id=principal["session_id"],
            auth_method=principal["auth_method"],
            credential_kind="user_session",
        )
    else:
        tenant_id, api_key = resolve_tenant_id_for_api_key(session, x_api_key, x_tenant_id)
        context = AuthContext(tenant_id=tenant_id, api_key=api_key)

    request.state.auth_context = context
    return context


def get_api_key_and_tenant(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="x-tenant-id")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    context = _resolve_request_auth_context(
        request=request,
        session=session,
        x_api_key=x_api_key,
        x_tenant_id=x_tenant_id,
        authorization=authorization,
    )
    ensure_tenant_writes_allowed_if_not_demo(request, session, context.tenant_id)
    return context.tenant_id


def get_optional_opa_user_role_header(
    x_opa_user_role: Annotated[str | None, Header(alias="x-opa-user-role")] = None,
) -> str | None:
    """
    Optional role hint for OPA.

    Honored only when COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER is enabled.
    """
    if x_opa_user_role is None:
        return None
    s = str(x_opa_user_role).strip()
    return s or None


def get_auth_context(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="x-tenant-id")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthContext:
    context = _resolve_request_auth_context(
        request=request,
        session=session,
        x_api_key=x_api_key,
        x_tenant_id=x_tenant_id,
        authorization=authorization,
    )
    ensure_tenant_writes_allowed_if_not_demo(request, session, context.tenant_id)
    return context


def require_path_tenant_matches_auth(tenant_id: str, auth: AuthContext) -> None:
    if tenant_id != auth.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id in path must match x-tenant-id",
        )
