"""Demo-Mandanten: keine Laufzeit-Events per API (nur Seeds/Intern)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, status

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def ensure_runtime_events_api_ingest_allowed(session: Session, tenant_id: str) -> None:
    """403 wenn registrierter Mandant als Demo markiert (externe Connectoren)."""
    from app.repositories.tenant_registry import TenantRegistryRepository

    row = TenantRegistryRepository(session).get_by_id(tenant_id)
    if row is not None and row.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Runtime event ingest is not available for demo tenants",
        )
