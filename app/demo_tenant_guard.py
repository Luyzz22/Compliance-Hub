"""Zentrale Policy: Demo-/Playground-Mandanten und Schreibschutz (ComplianceHub)."""

from __future__ import annotations

import os

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.repositories.tenant_registry import TenantRegistryRepository

DEMO_TENANT_READONLY_CODE = "demo_tenant_readonly"

__all__ = [
    "DEMO_TENANT_READONLY_CODE",
    "demo_readonly_blocks_mutations",
    "ensure_not_demo_readonly_tenant_or_raise",
    "ensure_tenant_writes_allowed_if_not_demo",
    "raise_if_demo_tenant_readonly",
    "tenant_mutation_blocked_meta",
]


def _env_truthy(key: str) -> bool:
    raw = os.getenv(key, "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def demo_readonly_blocks_mutations(session: Session, tenant_id: str) -> bool:
    """
    True, wenn Schreiboperationen für diesen Mandanten abgewiesen werden sollen.

    - is_demo und nicht demo_playground: blockieren
    - COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS: auch demo_playground blockieren (strenger Pilot)
    """
    row = TenantRegistryRepository(session).get_by_id(tenant_id)
    if row is None:
        return False
    if not row.is_demo:
        return False
    if _env_truthy("COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS"):
        return True
    return not row.demo_playground


def tenant_mutation_blocked_meta(session: Session, tenant_id: str) -> bool:
    """Synonym für API-/UI-Felder (mutation_blocked)."""
    return demo_readonly_blocks_mutations(session, tenant_id)


def raise_if_demo_tenant_readonly(session: Session, tenant_id: str) -> None:
    """403 mit stabilem code demo_tenant_readonly, wenn der Mandant schreibgeschützt ist."""
    if not demo_readonly_blocks_mutations(session, tenant_id):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": DEMO_TENANT_READONLY_CODE,
            "message": (
                "This tenant is read-only (demo). Use a production workspace or a sandbox "
                "tenant with demo_playground enabled."
            ),
        },
    )


def ensure_not_demo_readonly_tenant_or_raise(session: Session, tenant_id: str) -> None:
    """Expliziter Aufruf aus Routern (Alias zu raise_if_demo_tenant_readonly)."""
    raise_if_demo_tenant_readonly(session, tenant_id)


def ensure_tenant_writes_allowed_if_not_demo(
    request: Request,
    session: Session,
    tenant_id: str,
) -> None:
    """FastAPI-Auth-Pfad: bei mutierenden HTTP-Methoden Policy anwenden."""
    if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return
    raise_if_demo_tenant_readonly(session, tenant_id)
