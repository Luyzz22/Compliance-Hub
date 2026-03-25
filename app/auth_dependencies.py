"""FastAPI-Dependencies: Mandanten-Auth mit globalem Key-Pool (ENV) und tenant_api_keys (DB)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.demo_tenant_write_guard import ensure_tenant_writes_allowed_if_not_demo
from app.repositories.tenant_api_keys import TenantApiKeyRepository
from app.security import AuthContext, get_settings


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
    if api_key in settings.api_keys:
        return tenant_id, api_key

    repo = TenantApiKeyRepository(session)
    if repo.verify_key(tenant_id=tenant_id, raw_key=api_key):
        return tenant_id, api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
    )


def get_api_key_and_tenant(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="x-tenant-id")] = None,
) -> str:
    tid, _ = resolve_tenant_id_for_api_key(session, x_api_key, x_tenant_id)
    ensure_tenant_writes_allowed_if_not_demo(request, session, tid)
    return tid


def get_auth_context(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    x_api_key: Annotated[str | None, Header(alias="x-api-key")] = None,
    x_tenant_id: Annotated[str | None, Header(alias="x-tenant-id")] = None,
) -> AuthContext:
    tid, key = resolve_tenant_id_for_api_key(session, x_api_key, x_tenant_id)
    ensure_tenant_writes_allowed_if_not_demo(request, session, tid)
    return AuthContext(tenant_id=tid, api_key=key)


def require_path_tenant_matches_auth(tenant_id: str, auth: AuthContext) -> None:
    if tenant_id != auth.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="tenant_id in path must match x-tenant-id",
        )
