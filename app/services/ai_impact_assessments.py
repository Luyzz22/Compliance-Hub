from __future__ import annotations

from datetime import UTC, datetime

from app.ai_impact_assessment_models import (
    AIImpactAssessmentPortfolioResponse,
    AIImpactAssessmentRead,
    AIImpactAssessmentSummary,
    AIImpactAssessmentSystemRow,
    ImpactAssessmentLifecycle,
    ImpactAssessmentScope,
    ImpactResidualRisk,
    ImpactSectionStatus,
    PriorConsultationStatus,
)
from app.ai_system_models import AISystem
from app.repositories.ai_impact_assessments import AIImpactAssessmentRepository

_SECTION_SCORE = {
    ImpactSectionStatus.not_started: 0,
    ImpactSectionStatus.drafted: 25,
    ImpactSectionStatus.evidenced: 65,
    ImpactSectionStatus.reviewed: 100,
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _system_metrics(
    assessment: AIImpactAssessmentRead,
    *,
    registry_dpia_signal: bool,
    now: datetime,
) -> tuple[int, str, list[str], int, int, bool]:
    applicable = [
        section
        for section in assessment.sections
        if section.status != ImpactSectionStatus.not_applicable
    ]
    reviewed = [section for section in applicable if section.status == ImpactSectionStatus.reviewed]
    score = (
        round(sum(_SECTION_SCORE[section.status] for section in applicable) / len(applicable))
        if applicable
        else 0
    )
    review_overdue = bool(
        assessment.review_due_at_utc and _as_utc(assessment.review_due_at_utc) < now
    )
    blockers: list[str] = []
    if assessment.dpia_scope == ImpactAssessmentScope.undetermined:
        blockers.append("DSFA-Scope ist nicht entschieden")
    if assessment.fria_scope == ImpactAssessmentScope.undetermined:
        blockers.append("FRIA-Scope ist nicht entschieden")
    if registry_dpia_signal and assessment.dpia_scope == ImpactAssessmentScope.not_required:
        blockers.append("DSFA-Signal im KI-Register weicht von der Scope-Entscheidung ab")
    if assessment.dpia_scope == ImpactAssessmentScope.required and not assessment.dpo_involved:
        blockers.append("Einbindung der Datenschutzbeauftragten ist nicht dokumentiert")
    if assessment.residual_risk == ImpactResidualRisk.high and (
        assessment.prior_consultation_status != PriorConsultationStatus.closed
    ):
        blockers.append("Hohes Residualrisiko mit offenem Konsultations-Gate")
    if review_overdue:
        blockers.append("Wiedervorlage ist überfällig")
    if assessment.lifecycle_status == ImpactAssessmentLifecycle.approved and len(reviewed) < len(
        applicable
    ):
        blockers.append("Freigabestatus und Abschnittsreview sind inkonsistent")

    if review_overdue:
        posture = "review_overdue"
    elif assessment.version == 0 or (
        assessment.dpia_scope == ImpactAssessmentScope.undetermined
        or assessment.fria_scope == ImpactAssessmentScope.undetermined
    ):
        posture = "scope_incomplete"
    elif assessment.residual_risk == ImpactResidualRisk.high and (
        assessment.prior_consultation_status != PriorConsultationStatus.closed
    ):
        posture = "consultation_gate"
    elif assessment.lifecycle_status == ImpactAssessmentLifecycle.approved:
        posture = "approved"
    elif assessment.lifecycle_status == ImpactAssessmentLifecycle.remediation_required:
        posture = "remediation_required"
    elif assessment.lifecycle_status == ImpactAssessmentLifecycle.in_review:
        posture = "in_review"
    elif score >= 65:
        posture = "review_ready"
    else:
        posture = "draft"
    return score, posture, blockers, len(applicable), len(reviewed), review_overdue


def build_ai_impact_assessment_portfolio(
    tenant_id: str,
    ai_systems: list[AISystem],
    repository: AIImpactAssessmentRepository,
    *,
    now: datetime | None = None,
) -> AIImpactAssessmentPortfolioResponse:
    generated_at = _as_utc(now or datetime.now(UTC))
    stored = repository.list_for_tenant(tenant_id)
    rows: list[AIImpactAssessmentSystemRow] = []

    for system in sorted(ai_systems, key=lambda item: (item.name.casefold(), item.id)):
        assessment = stored.get(system.id) or repository.default_for_system(tenant_id, system.id)
        score, posture, blockers, applicable, reviewed, overdue = _system_metrics(
            assessment,
            registry_dpia_signal=system.gdpr_dpia_required,
            now=generated_at,
        )
        rows.append(
            AIImpactAssessmentSystemRow(
                ai_system_id=system.id,
                ai_system_name=system.name,
                business_unit=system.business_unit,
                risk_level=system.risk_level,
                ai_act_category=system.ai_act_category,
                registry_dpia_signal=system.gdpr_dpia_required,
                assessment=assessment,
                readiness_score_pct=score,
                posture=posture,
                blockers=blockers,
                applicable_sections=applicable,
                reviewed_sections=reviewed,
                review_overdue=overdue,
            )
        )

    total_systems = len(rows)
    assessed_systems = sum(row.assessment.version > 0 for row in rows)
    scope_open_count = sum(row.posture == "scope_incomplete" for row in rows)
    in_review_count = sum(row.posture in {"in_review", "review_ready"} for row in rows)
    approved_count = sum(row.posture == "approved" for row in rows)
    high_residual_risk_count = sum(
        row.assessment.residual_risk == ImpactResidualRisk.high for row in rows
    )
    consultation_open_count = sum(row.posture == "consultation_gate" for row in rows)
    overdue_review_count = sum(row.review_overdue for row in rows)
    readiness_score = (
        round(sum(row.readiness_score_pct for row in rows) / total_systems) if total_systems else 0
    )

    if total_systems == 0:
        posture = "no_ai_systems"
    elif overdue_review_count:
        posture = "review_overdue"
    elif consultation_open_count:
        posture = "consultation_gate"
    elif scope_open_count:
        posture = "scope_incomplete"
    elif approved_count == total_systems:
        posture = "approved"
    elif in_review_count:
        posture = "in_review"
    else:
        posture = "action_required"

    return AIImpactAssessmentPortfolioResponse(
        tenant_id=tenant_id,
        generated_at_utc=generated_at,
        readiness_score_pct=readiness_score,
        posture=posture,
        summary=AIImpactAssessmentSummary(
            total_systems=total_systems,
            assessed_systems=assessed_systems,
            scope_open_count=scope_open_count,
            in_review_count=in_review_count,
            approved_count=approved_count,
            high_residual_risk_count=high_residual_risk_count,
            consultation_open_count=consultation_open_count,
            overdue_review_count=overdue_review_count,
        ),
        systems=rows,
    )
