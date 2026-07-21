from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai_transparency_assurance_models import (
    AITransparencyAssessmentRead,
    AITransparencyAssessmentUpsert,
    AITransparencyAssuranceResponse,
)
from app.auth_dependencies import get_auth_context
from app.db import get_session
from app.rbac.dependencies import require_permission
from app.rbac.permissions import Permission
from app.rbac.roles import EnterpriseRole
from app.repositories.ai_systems import AISystemRepository
from app.repositories.ai_transparency_assessments import (
    AITransparencyAssessmentRepository,
    TransparencyAssessmentVersionConflict,
)
from app.repositories.audit import AuditRepository
from app.repositories.audit_logs import AuditLogRepository
from app.security import AuthContext
from app.services.ai_transparency_assurance import build_ai_transparency_assurance

router = APIRouter(prefix="/api/v1", tags=["transparency-assurance"])


def _audit_snapshot(assessment: AITransparencyAssessmentRead) -> str:
    """Minimized change record: no evidence paths or reviewer identifiers in the hash log."""
    return json.dumps(
        {
            "version": assessment.version,
            "role_scope": assessment.role_scope.value,
            "controls": {
                control.control_key.value: {
                    "status": control.status.value,
                    "evidence_attached": bool(control.evidence_reference),
                    "rationale_attached": bool(control.rationale),
                }
                for control in assessment.controls
            },
            "reviewed": assessment.reviewed_at_utc is not None,
            "review_due": assessment.review_due_at_utc.isoformat()
            if assessment.review_due_at_utc
            else None,
        },
        sort_keys=True,
    )


def _require_ai_system(
    session: Session,
    tenant_id: str,
    ai_system_id: str,
) -> None:
    if AISystemRepository(session).get_by_id(tenant_id, ai_system_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )


@router.get(
    "/transparency-assurance",
    response_model=AITransparencyAssuranceResponse,
)
def get_transparency_assurance(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.VIEW_TRANSPARENCY_ASSURANCE)),
    ],
) -> AITransparencyAssuranceResponse:
    return build_ai_transparency_assurance(
        auth_context.tenant_id,
        AISystemRepository(session).list_for_tenant(auth_context.tenant_id),
        AITransparencyAssessmentRepository(session),
    )


@router.get(
    "/ai-systems/{ai_system_id}/transparency-assurance",
    response_model=AITransparencyAssessmentRead,
)
def get_ai_system_transparency_assurance(
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.VIEW_TRANSPARENCY_ASSURANCE)),
    ],
) -> AITransparencyAssessmentRead:
    _require_ai_system(session, auth_context.tenant_id, ai_system_id)
    repository = AITransparencyAssessmentRepository(session)
    return repository.get(
        auth_context.tenant_id,
        ai_system_id,
    ) or repository.default_for_system(auth_context.tenant_id, ai_system_id)


@router.put(
    "/ai-systems/{ai_system_id}/transparency-assurance",
    response_model=AITransparencyAssessmentRead,
)
def put_ai_system_transparency_assurance(
    ai_system_id: str,
    body: AITransparencyAssessmentUpsert,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    role: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.MANAGE_TRANSPARENCY_ASSURANCE)),
    ],
) -> AITransparencyAssessmentRead:
    tenant_id = auth_context.tenant_id
    _require_ai_system(session, tenant_id, ai_system_id)
    repository = AITransparencyAssessmentRepository(session)
    before = repository.get(tenant_id, ai_system_id) or repository.default_for_system(
        tenant_id,
        ai_system_id,
    )
    try:
        updated = repository.upsert(
            tenant_id,
            ai_system_id,
            body,
            actor=auth_context.actor_id,
            commit=False,
        )
    except TransparencyAssessmentVersionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "transparency_assessment_version_conflict",
                "message": str(exc),
            },
        ) from exc

    AuditRepository(session).log_event(
        tenant_id=tenant_id,
        actor_type=auth_context.credential_kind,
        actor_id=auth_context.actor_id,
        entity_type="ai_transparency_assessment",
        entity_id=ai_system_id,
        action="upserted",
        metadata={
            "version": updated.version,
            "role_scope": updated.role_scope.value,
        },
        commit=False,
    )
    # record_event commits assessment, normalized event and hash-chain entry atomically.
    AuditLogRepository(session).record_event(
        tenant_id=tenant_id,
        actor=auth_context.actor_id,
        actor_role=role.value,
        action="update_transparency_assurance",
        entity_type="AITransparencyAssessment",
        entity_id=ai_system_id,
        before=_audit_snapshot(before),
        after=_audit_snapshot(updated),
        outcome="success",
        metadata_json=json.dumps(
            {
                "framework": "EU AI Act Art. 50 / GDPR Art. 12-14",
                "version": updated.version,
            },
            sort_keys=True,
        ),
    )
    return updated
