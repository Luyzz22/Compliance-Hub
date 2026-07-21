from __future__ import annotations

from datetime import UTC, datetime

from app.ai_system_models import AISystem
from app.ai_transparency_assurance_models import (
    AITransparencyAssessmentRead,
    AITransparencyAssuranceResponse,
    AITransparencyAssuranceSummary,
    AITransparencySystemRow,
    AIValueChainRole,
    TransparencyControlStatus,
)
from app.repositories.ai_transparency_assessments import AITransparencyAssessmentRepository

ARTICLE_50_APPLICATION_AT_UTC = datetime(2026, 8, 2, tzinfo=UTC)

_STATUS_SCORE = {
    TransparencyControlStatus.not_assessed: 0,
    TransparencyControlStatus.planned: 25,
    TransparencyControlStatus.implemented: 75,
    TransparencyControlStatus.verified: 100,
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _system_metrics(
    assessment: AITransparencyAssessmentRead,
    now: datetime,
) -> tuple[int, str, int, int, bool]:
    applicable = [
        control
        for control in assessment.controls
        if control.status != TransparencyControlStatus.not_applicable
    ]
    verified = [
        control for control in applicable if control.status == TransparencyControlStatus.verified
    ]
    score = (
        round(sum(_STATUS_SCORE[control.status] for control in applicable) / len(applicable))
        if applicable
        else 0
    )
    review_overdue = bool(
        assessment.review_due_at_utc and _as_utc(assessment.review_due_at_utc) < now
    )
    requires_scope = (
        assessment.version == 0
        or assessment.role_scope == AIValueChainRole.unknown
        or not applicable
    )
    if review_overdue:
        posture = "review_overdue"
    elif requires_scope:
        posture = "requires_scope"
    elif len(verified) == len(applicable):
        posture = "verified"
    elif score >= 75:
        posture = "implementation_pending_verification"
    elif score > 0:
        posture = "remediation_active"
    else:
        posture = "action_required"
    return score, posture, len(applicable), len(verified), review_overdue


def build_ai_transparency_assurance(
    tenant_id: str,
    ai_systems: list[AISystem],
    repository: AITransparencyAssessmentRepository,
    *,
    now: datetime | None = None,
) -> AITransparencyAssuranceResponse:
    generated_at = _as_utc(now or datetime.now(UTC))
    stored = repository.list_for_tenant(tenant_id)
    rows: list[AITransparencySystemRow] = []

    for system in sorted(ai_systems, key=lambda item: (item.name.casefold(), item.id)):
        assessment = stored.get(system.id) or repository.default_for_system(tenant_id, system.id)
        score, posture, applicable, verified, overdue = _system_metrics(
            assessment,
            generated_at,
        )
        rows.append(
            AITransparencySystemRow(
                ai_system_id=system.id,
                ai_system_name=system.name,
                business_unit=system.business_unit,
                risk_level=system.risk_level,
                ai_act_category=system.ai_act_category,
                assessment=assessment,
                readiness_score_pct=score,
                posture=posture,
                applicable_controls=applicable,
                verified_controls=verified,
                review_overdue=overdue,
            )
        )

    total_systems = len(rows)
    assessed_systems = sum(row.assessment.version > 0 for row in rows)
    requires_scope_count = sum(row.posture == "requires_scope" for row in rows)
    verified_systems = sum(row.posture == "verified" for row in rows)
    overdue_review_count = sum(row.review_overdue for row in rows)
    applicable_controls = sum(row.applicable_controls for row in rows)
    verified_controls = sum(row.verified_controls for row in rows)
    readiness_score = (
        round(sum(row.readiness_score_pct for row in rows) / total_systems) if total_systems else 0
    )
    if total_systems == 0:
        posture = "no_ai_systems"
    elif overdue_review_count:
        posture = "review_overdue"
    elif requires_scope_count:
        posture = "scope_incomplete"
    elif verified_systems == total_systems:
        posture = "verified"
    elif readiness_score >= 75:
        posture = "implementation_pending_verification"
    else:
        posture = "action_required"

    return AITransparencyAssuranceResponse(
        tenant_id=tenant_id,
        generated_at_utc=generated_at,
        article_50_application_at_utc=ARTICLE_50_APPLICATION_AT_UTC,
        days_until_application=(ARTICLE_50_APPLICATION_AT_UTC.date() - generated_at.date()).days,
        readiness_score_pct=readiness_score,
        posture=posture,
        summary=AITransparencyAssuranceSummary(
            total_systems=total_systems,
            assessed_systems=assessed_systems,
            requires_scope_count=requires_scope_count,
            verified_systems=verified_systems,
            overdue_review_count=overdue_review_count,
            applicable_controls=applicable_controls,
            verified_controls=verified_controls,
        ),
        systems=rows,
    )
