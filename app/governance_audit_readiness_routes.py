"""Audit readiness & evidence completeness over unified controls (MVP)."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_dependencies import get_api_key_and_tenant
from app.db import get_session
from app.governance_audit_readiness_models import (
    AuditReadinessControlRow,
    AuditReadinessSummaryRead,
    GovernanceAuditCaseCreate,
    GovernanceAuditCaseRead,
    GovernanceAuditTrailRow,
)
from app.governance_taxonomy import GovernanceAuditAction, GovernanceAuditEntity
from app.models_db import AuditLogTable
from app.rbac.roles import EnterpriseRole
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.governance_audit_readiness import GovernanceAuditReadinessRepository
from app.services.governance_audit import record_governance_audit


def get_audit_log_repository(
    session: Annotated[Session, Depends(get_session)],
) -> AuditLogRepository:
    return AuditLogRepository(session)


def get_governance_audit_readiness_repository(
    session: Annotated[Session, Depends(get_session)],
) -> GovernanceAuditReadinessRepository:
    return GovernanceAuditReadinessRepository(session)


router = APIRouter(prefix="/api/v1/governance/audits", tags=["governance", "audits"])


@router.get("", response_model=list[GovernanceAuditCaseRead])
def list_audit_cases(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[
        GovernanceAuditReadinessRepository,
        Depends(get_governance_audit_readiness_repository),
    ],
) -> list[GovernanceAuditCaseRead]:
    return repo.list_cases(tenant_id)


@router.post("", response_model=GovernanceAuditCaseRead, status_code=status.HTTP_201_CREATED)
def create_audit_case(
    body: GovernanceAuditCaseCreate,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[
        GovernanceAuditReadinessRepository,
        Depends(get_governance_audit_readiness_repository),
    ],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> GovernanceAuditCaseRead:
    try:
        created = repo.create_case(tenant_id, body, created_by="api:governance-audits")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id="api:governance-audits",
        actor_role=EnterpriseRole.COMPLIANCE_OFFICER,
        action=GovernanceAuditAction.GOVERNANCE_AUDIT_CASE_CREATE.value,
        entity_type=GovernanceAuditEntity.GOVERNANCE_AUDIT_CASE.value,
        entity_id=created.id,
        outcome="success",
        before=None,
        after=json.dumps({"title": created.title, "frameworks": created.framework_tags}),
        correlation_id=None,
        metadata={"control_count": len(created.control_ids)},
    )
    return created


@router.get("/{audit_id}", response_model=GovernanceAuditCaseRead)
def get_audit_case(
    audit_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[
        GovernanceAuditReadinessRepository,
        Depends(get_governance_audit_readiness_repository),
    ],
) -> GovernanceAuditCaseRead:
    row = repo.get_case(tenant_id, audit_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit case not found")
    return row


@router.get("/{audit_id}/readiness", response_model=AuditReadinessSummaryRead)
def get_audit_readiness(
    audit_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[
        GovernanceAuditReadinessRepository,
        Depends(get_governance_audit_readiness_repository),
    ],
) -> AuditReadinessSummaryRead:
    summary = repo.build_readiness(tenant_id, audit_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit case not found")
    return summary


@router.get("/{audit_id}/controls", response_model=list[AuditReadinessControlRow])
def list_audit_case_controls(
    audit_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[
        GovernanceAuditReadinessRepository,
        Depends(get_governance_audit_readiness_repository),
    ],
) -> list[AuditReadinessControlRow]:
    rows = repo.list_control_rows(tenant_id, audit_id)
    if rows is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit case not found")
    return rows


@router.get("/{audit_id}/trail", response_model=list[GovernanceAuditTrailRow])
def list_audit_case_trail(
    audit_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: Annotated[Session, Depends(get_session)],
    repo: Annotated[
        GovernanceAuditReadinessRepository,
        Depends(get_governance_audit_readiness_repository),
    ],
) -> list[GovernanceAuditTrailRow]:
    if repo.get_case(tenant_id, audit_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit case not found")
    stmt = (
        select(AuditLogTable)
        .where(
            AuditLogTable.tenant_id == tenant_id,
            AuditLogTable.entity_type == GovernanceAuditEntity.GOVERNANCE_AUDIT_CASE.value,
            AuditLogTable.entity_id == audit_id,
        )
        .order_by(AuditLogTable.created_at_utc.desc())
        .limit(200)
    )
    rows = session.scalars(stmt).all()
    return [
        GovernanceAuditTrailRow(
            created_at_utc=r.created_at_utc,
            actor=r.actor,
            action=r.action,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            outcome=r.outcome,
        )
        for r in rows
    ]


@router.post(
    "/{audit_id}/controls/{control_id}/attach",
    response_model=GovernanceAuditCaseRead,
)
def attach_control_to_audit_case(
    audit_id: str,
    control_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    repo: Annotated[
        GovernanceAuditReadinessRepository,
        Depends(get_governance_audit_readiness_repository),
    ],
    audit_repo: Annotated[AuditLogRepository, Depends(get_audit_log_repository)],
) -> GovernanceAuditCaseRead:
    updated = repo.attach_control(tenant_id, audit_id, control_id)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit case or control not found",
        )
    record_governance_audit(
        audit_repo,
        tenant_id=tenant_id,
        actor_id="api:governance-audits",
        actor_role=EnterpriseRole.COMPLIANCE_OFFICER,
        action=GovernanceAuditAction.GOVERNANCE_AUDIT_CASE_CONTROL_ATTACH.value,
        entity_type=GovernanceAuditEntity.GOVERNANCE_AUDIT_CASE.value,
        entity_id=audit_id,
        outcome="success",
        before=None,
        after=json.dumps({"control_id": control_id}),
        correlation_id=None,
        metadata=None,
    )
    return updated
