"""Tenant-scoped governance APIs: operational health snapshots & incidents."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth_dependencies import get_api_key_and_tenant
from app.db import get_session
from app.governance_taxonomy import GovernanceAuditAction, GovernanceAuditEntity
from app.operations_resilience_models import (
    IncidentResolveRequest,
    IncidentResolveResponse,
    OperationsKpisRead,
    ServiceHealthIncidentRead,
    ServiceHealthSnapshotRead,
)
from app.rbac.roles import EnterpriseRole
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.service_health import ServiceHealthRepository
from app.services.governance_audit import record_governance_audit

router = APIRouter(prefix="/api/v1/governance/operations", tags=["governance", "operations"])


def get_audit_log_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AuditLogRepository:
    return AuditLogRepository(session)


def get_service_health_repository(
    session: Annotated[Session, Depends(get_session)],
) -> ServiceHealthRepository:
    return ServiceHealthRepository(session)


@router.get("/kpis", response_model=OperationsKpisRead)
def get_operations_kpis(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[ServiceHealthRepository, Depends(get_service_health_repository)],
) -> OperationsKpisRead:
    latest = repo.latest_snapshot_statuses(tenant_id)
    degraded = sum(1 for s in latest.values() if s == "degraded")
    down = sum(1 for s in latest.values() if s == "down")
    return OperationsKpisRead(
        last_checked_at=repo.last_checked_at(tenant_id),
        open_incidents=repo.count_open_incidents(tenant_id),
        degraded_services=degraded,
        down_services=down,
    )


@router.get("/health/snapshots", response_model=list[ServiceHealthSnapshotRead])
def list_health_snapshots(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[ServiceHealthRepository, Depends(get_service_health_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ServiceHealthSnapshotRead]:
    rows = repo.list_snapshots(tenant_id, limit=limit)
    return [
        ServiceHealthSnapshotRead(
            id=r.id,
            tenant_id=r.tenant_id,
            poll_run_id=r.poll_run_id,
            source=r.source,
            service_name=r.service_name,
            status=r.status,
            checked_at=r.checked_at,
        )
        for r in rows
    ]


@router.get("/incidents", response_model=list[ServiceHealthIncidentRead])
def list_health_incidents(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[ServiceHealthRepository, Depends(get_service_health_repository)],
    open_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ServiceHealthIncidentRead]:
    rows = repo.list_incidents(tenant_id, open_only=open_only, limit=limit)
    return [
        ServiceHealthIncidentRead(
            id=r.id,
            tenant_id=r.tenant_id,
            service_name=r.service_name,
            previous_status=r.previous_status,
            current_status=r.current_status,
            severity=r.severity,
            incident_state=r.incident_state,
            source=r.source,
            detected_at=r.detected_at,
            resolved_at=r.resolved_at,
            title=r.title,
            summary=r.summary,
        )
        for r in rows
    ]


@router.patch("/incidents/{incident_id}/resolve", response_model=IncidentResolveResponse)
def resolve_health_incident(
    incident_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[ServiceHealthRepository, Depends(get_service_health_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
    body: IncidentResolveRequest | None = Body(default=None),
) -> IncidentResolveResponse:
    when = datetime.now(UTC)
    ok = repo.mark_incident_resolved(tenant_id, incident_id, when)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found or not open",
        )
    note = body.resolved_note if body is not None else None
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id="api:tenant_user",
        actor_role=EnterpriseRole.COMPLIANCE_OFFICER,
        action=GovernanceAuditAction.SERVICE_HEALTH_INCIDENT_RESOLVED.value,
        entity_type=GovernanceAuditEntity.SERVICE_HEALTH_INCIDENT.value,
        entity_id=incident_id,
        outcome="success",
        before=None,
        after=json.dumps({"resolved_at": when.isoformat(), "note": note}),
        correlation_id=None,
        metadata={"manual_resolve": True},
    )
    return IncidentResolveResponse(
        id=incident_id,
        incident_state="resolved",
        resolved_at=when,
    )
