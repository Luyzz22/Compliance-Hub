"""Zentrale Policy: Demo-/Playground-Mandanten und Schreibschutz (ComplianceHub)."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.repositories.tenant_registry import TenantRegistryRepository
from app.services import usage_event_logger

DEMO_TENANT_READONLY_CODE = "demo_tenant_readonly"

WorkspaceModeTelemetry = Literal["production", "demo", "playground", "unknown"]

__all__ = [
    "DEMO_TENANT_READONLY_CODE",
    "WorkspaceModeTelemetry",
    "compute_workspace_mode_ui",
    "demo_readonly_blocks_mutations",
    "demo_readonly_error_detail",
    "demo_readonly_http_exception",
    "ensure_not_demo_readonly_tenant_or_raise",
    "ensure_tenant_writes_allowed_if_not_demo",
    "raise_if_demo_tenant_readonly",
    "route_template_for_request",
    "tenant_mutation_blocked_meta",
    "workspace_mode_for_telemetry",
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


def workspace_mode_for_telemetry(session: Session, tenant_id: str) -> WorkspaceModeTelemetry:
    """Klassifikation für Usage-Events (keine PII): production | demo | playground."""
    row = TenantRegistryRepository(session).get_by_id(tenant_id)
    if row is None:
        return "unknown"
    if not row.is_demo:
        return "production"
    if row.demo_playground:
        return "playground"
    return "demo"


def compute_workspace_mode_ui(
    *,
    is_demo: bool,
    demo_playground: bool,
    mutation_blocked: bool,
) -> tuple[Literal["production", "demo", "playground"], str, str]:
    """
    UI-Vertrag für Workspace-Shell (deutsche Kurztexte).

    Returns (workspace_mode, mode_label, mode_hint).
    """
    if not is_demo:
        return (
            "production",
            "Produktiv-Mandant",
            "Änderungen werden normal über die API persistiert.",
        )
    if mutation_blocked:
        return (
            "demo",
            "Demo (schreibgeschützt)",
            "Volle Governance-Ansicht; Schreibzugriffe werden mit 403 abgewiesen.",
        )
    return (
        "playground",
        "Playground",
        "Sandbox: begrenzte Schreiboperationen möglich — keine Produktivdaten.",
    )


def route_template_for_request(request: Request) -> str:
    """OpenAPI-Pfad-Template wenn verfügbar (ohne konkrete IDs in variablen Pfaden)."""
    route = request.scope.get("route")
    if route is not None:
        path = getattr(route, "path", None)
        if path:
            return str(path)
    return request.url.path


def demo_readonly_error_detail() -> dict[str, str]:
    """Stabiler API-Fehlerkörper (Englisch) inkl. Hint für Clients und Monitoring."""
    return {
        "code": DEMO_TENANT_READONLY_CODE,
        "message": (
            "This tenant is read-only (demo). Use a production workspace or a sandbox "
            "tenant with demo_playground enabled."
        ),
        "hint": (
            "Write operations are blocked for this demo tenant. Use a production tenant "
            "or a playground sandbox for exercises that require persistence."
        ),
    }


def demo_readonly_http_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=demo_readonly_error_detail(),
    )


def _log_demo_mutation_blocked(session: Session, tenant_id: str, request: Request) -> None:
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        usage_event_logger.DEMO_MUTATION_BLOCKED,
        {
            "http_method": str(request.method).upper(),
            "route": route_template_for_request(request),
            "workspace_mode": workspace_mode_for_telemetry(session, tenant_id),
        },
    )


def raise_if_demo_tenant_readonly(
    session: Session,
    tenant_id: str,
    *,
    request: Request | None = None,
) -> None:
    """403 mit code demo_tenant_readonly; optional Telemetrie bei blockiertem Schreibversuch."""
    if not demo_readonly_blocks_mutations(session, tenant_id):
        return
    if request is not None:
        _log_demo_mutation_blocked(session, tenant_id, request)
    raise demo_readonly_http_exception()


def ensure_not_demo_readonly_tenant_or_raise(
    session: Session,
    tenant_id: str,
    *,
    request: Request | None = None,
) -> None:
    """Expliziter Aufruf aus Routern (Alias zu raise_if_demo_tenant_readonly)."""
    raise_if_demo_tenant_readonly(session, tenant_id, request=request)


def ensure_tenant_writes_allowed_if_not_demo(
    request: Request,
    session: Session,
    tenant_id: str,
) -> None:
    """FastAPI-Auth-Pfad: bei mutierenden HTTP-Methoden Policy anwenden."""
    if request.method in ("GET", "HEAD", "OPTIONS", "TRACE"):
        return
    raise_if_demo_tenant_readonly(session, tenant_id, request=request)
