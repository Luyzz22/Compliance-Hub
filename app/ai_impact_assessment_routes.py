from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai_impact_assessment_models import (
    AIImpactAssessmentPortfolioResponse,
    AIImpactAssessmentRead,
    AIImpactAssessmentUpsert,
)
from app.auth_dependencies import get_auth_context
from app.db import get_session
from app.rbac.dependencies import require_permission
from app.rbac.permissions import Permission
from app.rbac.roles import EnterpriseRole
from app.repositories.ai_impact_assessments import (
    AIImpactAssessmentRepository,
    ImpactAssessmentVersionConflict,
)
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditRepository
from app.repositories.audit_logs import AuditLogRepository
from app.security import AuthContext
from app.services.ai_impact_assessments import build_ai_impact_assessment_portfolio

router = APIRouter(prefix="/api/v1", tags=["impact-assessments"])


def _audit_snapshot(assessment: AIImpactAssessmentRead) -> str:
    """Minimized hash-log snapshot without narrative, evidence or role identifiers."""
    return json.dumps(
        {
            "version": assessment.version,
            "dpia_scope": assessment.dpia_scope.value,
            "fria_scope": assessment.fria_scope.value,
            "deployer_context": assessment.deployer_context.value,
            "lifecycle_status": assessment.lifecycle_status.value,
            "residual_risk": assessment.residual_risk.value,
            "dpo_involved": assessment.dpo_involved,
            "stakeholder_views_status": assessment.stakeholder_views_status.value,
            "prior_consultation_status": assessment.prior_consultation_status.value,
            "consultation_reference_attached": bool(assessment.prior_consultation_reference),
            "sections": {
                section.section_key.value: {
                    "status": section.status.value,
                    "summary_attached": bool(section.summary),
                    "evidence_attached": bool(section.evidence_reference),
                    "rationale_attached": bool(section.rationale),
                }
                for section in assessment.sections
            },
            "reviewed": assessment.reviewed_at_utc is not None,
            "approved": assessment.approved_at_utc is not None,
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
    "/impact-assessments",
    response_model=AIImpactAssessmentPortfolioResponse,
)
def get_impact_assessment_portfolio(
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.VIEW_IMPACT_ASSESSMENTS)),
    ],
) -> AIImpactAssessmentPortfolioResponse:
    tenant_id = auth_context.tenant_id
    return build_ai_impact_assessment_portfolio(
        tenant_id,
        AISystemRepository(session).list_for_tenant(tenant_id),
        AIImpactAssessmentRepository(session),
    )


@router.get(
    "/ai-systems/{ai_system_id}/impact-assessment",
    response_model=AIImpactAssessmentRead,
)
def get_ai_system_impact_assessment(
    ai_system_id: str,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    _role: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.VIEW_IMPACT_ASSESSMENTS)),
    ],
) -> AIImpactAssessmentRead:
    tenant_id = auth_context.tenant_id
    _require_ai_system(session, tenant_id, ai_system_id)
    repository = AIImpactAssessmentRepository(session)
    return repository.get(tenant_id, ai_system_id) or repository.default_for_system(
        tenant_id,
        ai_system_id,
    )


@router.put(
    "/ai-systems/{ai_system_id}/impact-assessment",
    response_model=AIImpactAssessmentRead,
)
def put_ai_system_impact_assessment(
    ai_system_id: str,
    body: AIImpactAssessmentUpsert,
    auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    session: Annotated[Session, Depends(get_session)],
    role: Annotated[
        EnterpriseRole,
        Depends(require_permission(Permission.MANAGE_IMPACT_ASSESSMENTS)),
    ],
) -> AIImpactAssessmentRead:
    tenant_id = auth_context.tenant_id
    _require_ai_system(session, tenant_id, ai_system_id)
    repository = AIImpactAssessmentRepository(session)
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
    except ImpactAssessmentVersionConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "impact_assessment_version_conflict",
                "message": str(exc),
            },
        ) from exc

    AuditRepository(session).log_event(
        tenant_id=tenant_id,
        actor_type=auth_context.credential_kind,
        actor_id=auth_context.actor_id,
        entity_type="ai_impact_assessment",
        entity_id=ai_system_id,
        action="upserted",
        metadata={
            "version": updated.version,
            "lifecycle_status": updated.lifecycle_status.value,
            "dpia_scope": updated.dpia_scope.value,
            "fria_scope": updated.fria_scope.value,
        },
        commit=False,
    )
    # The hash-log commit closes assessment, normalized event and change record atomically.
    AuditLogRepository(session).record_event(
        tenant_id=tenant_id,
        actor=auth_context.actor_id,
        actor_role=role.value,
        action="update_ai_impact_assessment",
        entity_type="AIImpactAssessment",
        entity_id=ai_system_id,
        before=_audit_snapshot(before),
        after=_audit_snapshot(updated),
        outcome="success",
        metadata_json=json.dumps(
            {
                "framework": "GDPR Art. 35-36 / EU AI Act Art. 27",
                "version": updated.version,
            },
            sort_keys=True,
        ),
    )
    return updated
