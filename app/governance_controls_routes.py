"""Unified Control Layer: tenant controls, evidence, dashboard (MVP)."""

from __future__ import annotations

import csv
import io
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth_dependencies import get_api_key_and_tenant
from app.db import get_session
from app.governance_control_models import (
    GovernanceControlCreate,
    GovernanceControlEvidenceCreate,
    GovernanceControlEvidenceRead,
    GovernanceControlMaterializeRequest,
    GovernanceControlRead,
    GovernanceControlsDashboardSummary,
    GovernanceControlStatusHistoryRead,
    GovernanceControlSuggestion,
    GovernanceControlUpdate,
)
from app.governance_taxonomy import GovernanceAuditAction, GovernanceAuditEntity
from app.rbac.roles import EnterpriseRole
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.governance_controls import GovernanceControlRepository
from app.services.governance_audit import record_governance_audit
from app.services.governance_control_suggestions import suggest_governance_controls

router = APIRouter(prefix="/api/v1/governance/controls", tags=["governance", "controls"])


def get_audit_log_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AuditLogRepository:
    return AuditLogRepository(session)


def get_governance_control_repository(
    session: Annotated[Session, Depends(get_session)],
) -> GovernanceControlRepository:
    return GovernanceControlRepository(session)


@router.get("/suggestions", response_model=list[GovernanceControlSuggestion])
def list_control_suggestions(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
) -> list[GovernanceControlSuggestion]:
    """Deterministic templates from NIS2/KRITIS heuristics, AI register, operational health."""
    return suggest_governance_controls(session, tenant_id)


@router.get("/dashboard/summary", response_model=GovernanceControlsDashboardSummary)
def controls_dashboard_summary(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[GovernanceControlRepository, Depends(get_governance_control_repository)],
) -> GovernanceControlsDashboardSummary:
    return repo.dashboard_summary(tenant_id)


@router.get("/export")
def export_controls_csv(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[GovernanceControlRepository, Depends(get_governance_control_repository)],
) -> Response:
    """Board / audit office: tabular export (UTF-8, semicolon for Excel DE)."""
    rows = repo.list_controls_for_export(tenant_id)
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "id",
            "title",
            "status",
            "owner",
            "next_review_at_utc",
            "framework_tags",
            "framework_mappings",
            "created_at_utc",
            "updated_at_utc",
        ]
    )
    for r in rows:
        mappings = " | ".join(f"{m.framework}:{m.clause_ref}" for m in r.framework_mappings)
        writer.writerow(
            [
                r.id,
                r.title,
                r.status,
                r.owner or "",
                r.next_review_at.isoformat() if r.next_review_at else "",
                ",".join(r.framework_tags),
                mappings,
                r.created_at_utc.isoformat(),
                r.updated_at_utc.isoformat(),
            ]
        )
    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="governance_controls_export.csv"',
        },
    )


@router.post(
    "/from-suggestion",
    response_model=GovernanceControlRead,
    status_code=status.HTTP_201_CREATED,
)
def materialize_control_from_suggestion(
    body: GovernanceControlMaterializeRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    repo: Annotated[GovernanceControlRepository, Depends(get_governance_control_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> GovernanceControlRead | JSONResponse:
    """Idempotent: existing materialization returns HTTP 200 with the same body (no duplicate)."""
    existing = repo.find_materialized_suggestion(tenant_id, body.suggestion_key)
    if existing is not None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(existing),
        )
    suggestions = suggest_governance_controls(session, tenant_id)
    match = next((s for s in suggestions if s.suggestion_key == body.suggestion_key), None)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not applicable for this tenant or unknown key",
        )
    create = GovernanceControlCreate(
        title=match.title,
        description=match.description,
        status="not_started",
        framework_tags=list(match.framework_tags),
        framework_mappings=list(match.framework_mappings),
        source_inputs={
            "materialized_from_suggestion": match.suggestion_key,
            "triggered_by": match.triggered_by,
        },
    )
    try:
        created = repo.create_control(tenant_id, create, created_by="api:governance-controls")
    except IntegrityError:
        session.rollback()
        dup = repo.find_materialized_suggestion(tenant_id, body.suggestion_key)
        if dup is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Materialize conflict; retry or contact support",
            ) from None
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(dup),
        )
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id="api:governance-controls",
        actor_role=EnterpriseRole.COMPLIANCE_OFFICER,
        action=GovernanceAuditAction.GOVERNANCE_CONTROL_CREATE.value,
        entity_type=GovernanceAuditEntity.GOVERNANCE_CONTROL.value,
        entity_id=created.id,
        outcome="success",
        before=None,
        after=json.dumps(
            {"title": created.title, "materialized_from": match.suggestion_key},
        ),
        correlation_id=None,
        metadata={"source": "from_suggestion"},
    )
    return created


@router.get("", response_model=list[GovernanceControlRead])
def list_controls(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[GovernanceControlRepository, Depends(get_governance_control_repository)],
    response: Response,
    framework_tag: Annotated[str | None, Query(description="Filter by framework tag")] = None,
    search: Annotated[str | None, Query(max_length=200, description="Title substring")] = None,
    offset: Annotated[int, Query(ge=0, le=50_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> list[GovernanceControlRead]:
    items, total = repo.list_controls_page(
        tenant_id,
        framework_tag=framework_tag,
        search=search,
        offset=offset,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page-Offset"] = str(offset)
    response.headers["X-Page-Limit"] = str(limit)
    return items


@router.post("", response_model=GovernanceControlRead, status_code=status.HTTP_201_CREATED)
def create_control(
    body: GovernanceControlCreate,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[GovernanceControlRepository, Depends(get_governance_control_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> GovernanceControlRead:
    created = repo.create_control(tenant_id, body, created_by="api:governance-controls")
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id="api:governance-controls",
        actor_role=EnterpriseRole.COMPLIANCE_OFFICER,
        action=GovernanceAuditAction.GOVERNANCE_CONTROL_CREATE.value,
        entity_type=GovernanceAuditEntity.GOVERNANCE_CONTROL.value,
        entity_id=created.id,
        outcome="success",
        before=None,
        after=json.dumps({"title": created.title, "status": created.status}),
        correlation_id=None,
        metadata={"framework_tags": created.framework_tags},
    )
    return created


@router.get("/{control_id}/evidence", response_model=list[GovernanceControlEvidenceRead])
def list_control_evidence(
    control_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[GovernanceControlRepository, Depends(get_governance_control_repository)],
) -> list[GovernanceControlEvidenceRead]:
    if repo.get_control(tenant_id, control_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")
    return repo.list_evidence(tenant_id, control_id)


@router.get("/{control_id}/status-history", response_model=list[GovernanceControlStatusHistoryRead])
def list_control_status_history(
    control_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[GovernanceControlRepository, Depends(get_governance_control_repository)],
) -> list[GovernanceControlStatusHistoryRead]:
    if repo.get_control(tenant_id, control_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")
    return repo.list_status_history(tenant_id, control_id)


@router.get("/{control_id}", response_model=GovernanceControlRead)
def get_control(
    control_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[GovernanceControlRepository, Depends(get_governance_control_repository)],
) -> GovernanceControlRead:
    row = repo.get_control(tenant_id, control_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")
    return row


@router.patch("/{control_id}", response_model=GovernanceControlRead)
def patch_control(
    control_id: str,
    body: GovernanceControlUpdate,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[GovernanceControlRepository, Depends(get_governance_control_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> GovernanceControlRead:
    before = repo.get_control(tenant_id, control_id)
    if before is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")
    updated = repo.update_control(tenant_id, control_id, body, changed_by="api:governance-controls")
    assert updated is not None
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id="api:governance-controls",
        actor_role=EnterpriseRole.COMPLIANCE_OFFICER,
        action=GovernanceAuditAction.GOVERNANCE_CONTROL_UPDATE.value,
        entity_type=GovernanceAuditEntity.GOVERNANCE_CONTROL.value,
        entity_id=control_id,
        outcome="success",
        before=json.dumps({"status": before.status, "owner": before.owner}),
        after=json.dumps({"status": updated.status, "owner": updated.owner}),
        correlation_id=None,
        metadata=None,
    )
    return updated


@router.post(
    "/{control_id}/evidence",
    response_model=GovernanceControlEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def add_control_evidence(
    control_id: str,
    body: GovernanceControlEvidenceCreate,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[GovernanceControlRepository, Depends(get_governance_control_repository)],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> GovernanceControlEvidenceRead:
    ev = repo.add_evidence(tenant_id, control_id, body, created_by="api:governance-controls")
    if ev is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Control not found")
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id="api:governance-controls",
        actor_role=EnterpriseRole.COMPLIANCE_OFFICER,
        action=GovernanceAuditAction.GOVERNANCE_CONTROL_EVIDENCE_ADD.value,
        entity_type=GovernanceAuditEntity.GOVERNANCE_CONTROL_EVIDENCE.value,
        entity_id=ev.id,
        outcome="success",
        before=None,
        after=json.dumps({"control_id": control_id, "title": ev.title}),
        correlation_id=None,
        metadata={"source_type": ev.source_type},
    )
    return ev
