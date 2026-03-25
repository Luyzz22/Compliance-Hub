"""Schreibschutz für Demo-Mandanten (is_demo), optional aufgehoben bei demo_playground."""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.repositories.tenant_registry import TenantRegistryRepository


def ensure_tenant_writes_allowed_if_not_demo(
    request: Request,
    session: Session,
    tenant_id: str,
) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return
    row = TenantRegistryRepository(session).get_by_id(tenant_id)
    if row is None:
        return
    if row.is_demo and not row.demo_playground:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This demo tenant is read-only. Use a non-demo workspace to persist changes.",
        )
