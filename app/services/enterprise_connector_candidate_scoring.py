from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.enterprise_connector_candidate_models import (
    ConnectorCandidatePriority,
    ConnectorScoringWeights,
    EnterpriseConnectorCandidateRow,
    EnterpriseConnectorCandidatesResponse,
    ImplementationComplexityBand,
)
from app.enterprise_integration_blueprint_models import (
    EnterpriseIntegrationBlueprintRow,
    EvidenceDomain,
    IntegrationBlueprintStatus,
    SourceSystemType,
)
from app.enterprise_onboarding_models import (
    EnterpriseOnboardingReadinessResponse,
    IntegrationReadinessStatus,
    ReadinessStatus,
)
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.compliance_deadlines import ComplianceDeadlineRepository
from app.repositories.nis2_incidents import NIS2IncidentRepository
from app.services.enterprise_control_center import build_enterprise_control_center

SCORING_WEIGHTS = ConnectorScoringWeights()

_STRATEGIC_BASE: dict[SourceSystemType, int] = {
    SourceSystemType.sap_s4hana: 85,
    SourceSystemType.sap_btp: 80,
    SourceSystemType.datev: 72,
    SourceSystemType.ms_dynamics: 68,
    SourceSystemType.generic_api: 55,
}

_COMPLEXITY_BASE: dict[SourceSystemType, int] = {
    SourceSystemType.sap_s4hana: 76,
    SourceSystemType.sap_btp: 71,
    SourceSystemType.datev: 45,
    SourceSystemType.ms_dynamics: 60,
    SourceSystemType.generic_api: 42,
}

_COMPLIANCE_DOMAIN_SCORE: dict[EvidenceDomain, int] = {
    EvidenceDomain.invoice: 14,
    EvidenceDomain.approval: 14,
    EvidenceDomain.access: 18,
    EvidenceDomain.vendor: 10,
    EvidenceDomain.ai_inventory: 14,
    EvidenceDomain.policy_artifact: 10,
    EvidenceDomain.workflow_evidence: 12,
    EvidenceDomain.tax_export_context: 12,
}


def build_connector_candidates_response(
    *,
    tenant_id: str,
    session: Session,
    onboarding: EnterpriseOnboardingReadinessResponse | None,
    blueprints: list[EnterpriseIntegrationBlueprintRow],
    audit_repo: AuditLogRepository,
    incident_repo: NIS2IncidentRepository,
    deadline_repo: ComplianceDeadlineRepository,
    ai_repo: AISystemRepository,
    include_markdown: bool,
) -> EnterpriseConnectorCandidatesResponse:
    now = datetime.now(UTC)
    cc = build_enterprise_control_center(
        tenant_id=tenant_id,
        session=session,
        audit_repo=audit_repo,
        incident_repo=incident_repo,
        deadline_repo=deadline_repo,
        ai_repo=ai_repo,
        include_markdown=False,
    )
    rows = [
        _score_row(
            tenant_id=tenant_id,
            blueprint=bp,
            onboarding=onboarding,
            cc_open=cc.summary_counts.total_open,
        )
        for bp in blueprints
    ]
    rows_sorted = sorted(rows, key=lambda r: r.score_total, reverse=True)
    grouped = {row.connector_type.value: [row] for row in rows_sorted}
    markdown = _build_markdown(tenant_id, rows_sorted) if include_markdown else None
    return EnterpriseConnectorCandidatesResponse(
        tenant_id=tenant_id,
        generated_at_utc=now,
        scoring_weights=SCORING_WEIGHTS,
        candidate_rows=rows_sorted,
        top_priorities=[r for r in rows_sorted if r.recommended_priority in {"high", "medium"}][:5],
        grouped_priorities_by_connector_type=grouped,
        markdown_de=markdown,
    )


def _score_row(
    *,
    tenant_id: str,
    blueprint: EnterpriseIntegrationBlueprintRow,
    onboarding: EnterpriseOnboardingReadinessResponse | None,
    cc_open: int,
) -> EnterpriseConnectorCandidateRow:
    readiness = _readiness_score(blueprint, onboarding)
    blocker = _blocker_score(blueprint, onboarding)
    strategic = _strategic_value_score(blueprint, onboarding)
    compliance = _compliance_impact_score(blueprint, cc_open)
    complexity = _complexity_score(blueprint)

    weighted = (
        readiness * SCORING_WEIGHTS.readiness_weight
        + (100 - blocker) * SCORING_WEIGHTS.blocker_weight
        + strategic * SCORING_WEIGHTS.strategic_value_weight
        + compliance * SCORING_WEIGHTS.compliance_impact_weight
    ) / 100
    score_total = int(max(0, min(100, round(weighted))))

    if score_total >= 78 and blocker <= 35:
        priority = ConnectorCandidatePriority.high
    elif score_total >= 60 and blocker <= 55:
        priority = ConnectorCandidatePriority.medium
    elif score_total >= 45:
        priority = ConnectorCandidatePriority.low
    else:
        priority = ConnectorCandidatePriority.not_now

    if complexity >= 70:
        complexity_band = ImplementationComplexityBand.high
    elif complexity >= 45:
        complexity_band = ImplementationComplexityBand.medium
    else:
        complexity_band = ImplementationComplexityBand.low

    rationale_factors = [
        f"Readiness {readiness}/100",
        f"Blocker-Belastung {blocker}/100",
        f"Strategischer Wert {strategic}/100 ({blueprint.source_system_type.value})",
        f"Compliance-Impact {compliance}/100",
        f"Komplexität {complexity}/100 ({complexity_band.value})",
    ]
    rationale_summary = (
        f"{blueprint.source_system_type.value} ist als {priority.value} priorisiert "
        f"(Gesamtscore {score_total}/100)."
    )
    return EnterpriseConnectorCandidateRow(
        tenant_id=tenant_id,
        connector_type=blueprint.source_system_type,
        readiness_score=readiness,
        blocker_score=blocker,
        strategic_value_score=strategic,
        compliance_impact_score=compliance,
        estimated_implementation_complexity=complexity,
        complexity_band=complexity_band,
        recommended_priority=priority,
        rationale_summary_de=rationale_summary,
        rationale_factors_de=rationale_factors,
        score_total=score_total,
    )


def _readiness_score(
    blueprint: EnterpriseIntegrationBlueprintRow,
    onboarding: EnterpriseOnboardingReadinessResponse | None,
) -> int:
    score = 35
    if blueprint.integration_status == IntegrationBlueprintStatus.ready_for_build:
        score += 35
    elif blueprint.integration_status == IntegrationBlueprintStatus.designing:
        score += 20
    elif blueprint.integration_status == IntegrationBlueprintStatus.blocked:
        score -= 15

    if blueprint.data_owner:
        score += 10
    if blueprint.technical_owner:
        score += 10
    if blueprint.security_prerequisites:
        score += 10

    if onboarding is not None:
        sso = onboarding.sso_readiness
        if sso.onboarding_status == ReadinessStatus.validated:
            score += 10
        elif sso.onboarding_status in {ReadinessStatus.not_started, ReadinessStatus.planned}:
            score -= 8
        if sso.role_mapping_status == ReadinessStatus.validated:
            score += 8
        for item in onboarding.integration_readiness:
            if item.target_type.value != blueprint.source_system_type.value:
                continue
            if item.readiness_status == IntegrationReadinessStatus.ready_for_implementation:
                score += 10
            elif item.readiness_status == IntegrationReadinessStatus.mapped:
                score += 6
            elif item.readiness_status == IntegrationReadinessStatus.discovery:
                score += 2
            if item.owner:
                score += 4
            if item.blocker:
                score -= 8
    return max(0, min(100, score))


def _blocker_score(
    blueprint: EnterpriseIntegrationBlueprintRow,
    onboarding: EnterpriseOnboardingReadinessResponse | None,
) -> int:
    score = min(100, len(blueprint.blockers) * 20)
    if not blueprint.data_owner or not blueprint.technical_owner:
        score += 15
    if not blueprint.security_prerequisites:
        score += 15
    if onboarding is not None:
        score += min(35, len(onboarding.blockers) * 6)
    return max(0, min(100, score))


def _strategic_value_score(
    blueprint: EnterpriseIntegrationBlueprintRow,
    onboarding: EnterpriseOnboardingReadinessResponse | None,
) -> int:
    score = _STRATEGIC_BASE[blueprint.source_system_type]
    score += min(10, len(blueprint.evidence_domains) * 2)
    if blueprint.source_system_type in {SourceSystemType.sap_s4hana, SourceSystemType.sap_btp}:
        score += 5
    if onboarding is not None:
        sap_targets = {
            item.target_type.value
            for item in onboarding.integration_readiness
            if item.target_type.value
            in {SourceSystemType.sap_s4hana.value, SourceSystemType.sap_btp.value}
        }
        if sap_targets and blueprint.source_system_type.value in sap_targets:
            score += 8
    return max(0, min(100, score))


def _compliance_impact_score(
    blueprint: EnterpriseIntegrationBlueprintRow,
    cc_open: int,
) -> int:
    score = 20
    score += sum(_COMPLIANCE_DOMAIN_SCORE.get(d, 0) for d in blueprint.evidence_domains[:6])
    if cc_open >= 10:
        score += 10
    elif cc_open >= 5:
        score += 6
    return max(0, min(100, score))


def _complexity_score(blueprint: EnterpriseIntegrationBlueprintRow) -> int:
    score = _COMPLEXITY_BASE[blueprint.source_system_type]
    score += min(12, len(blueprint.evidence_domains) * 2)
    if blueprint.integration_status == IntegrationBlueprintStatus.ready_for_build:
        score -= 8
    if blueprint.integration_status == IntegrationBlueprintStatus.blocked:
        score += 8
    return max(0, min(100, score))


def _build_markdown(tenant_id: str, rows: list[EnterpriseConnectorCandidateRow]) -> str:
    lines = [
        "# Connector Candidates (Wave 56)",
        "",
        f"- Mandant: {tenant_id}",
        "- Hinweis: Explainable Rule-Based Scoring (kein ML-Lead-Scoring).",
        "",
        "## Top-Prioritäten",
    ]
    for row in rows[:5]:
        lines.append(
            f"- {row.connector_type.value}: {row.recommended_priority.value} "
            f"({row.score_total}/100) - {row.rationale_summary_de}"
        )
    lines.extend(["", "## Empfohlener Erst-Connector"])
    if rows:
        top = rows[0]
        lines.append(
            f"- {top.connector_type.value} ({top.recommended_priority.value}) "
            f"mit Score {top.score_total}/100."
        )
        lines.append(f"- Haupt-Blocker-Score: {top.blocker_score}/100.")
    else:
        lines.append("- Keine Connector-Kandidaten vorhanden.")
    return "\n".join(lines).strip() + "\n"
