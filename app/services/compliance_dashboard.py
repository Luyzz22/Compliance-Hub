"""Compliance-Dashboard und Board-Compliance-Overview (EU AI Act, ISO 42001)."""

from __future__ import annotations

from datetime import date

from app.compliance_gap_models import (
    REQUIREMENTS_BY_ID,
    AIComplianceOverview,
    ComplianceDashboard,
    ComplianceStatus,
    ComplianceStatusEntry,
    SystemReadiness,
    TopCriticalRequirement,
)
from app.repositories.ai_systems import AISystemRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_gap import ComplianceGapRepository

EU_AI_ACT_HIGH_RISK_DEADLINE = date(2026, 8, 2)


def compute_compliance_dashboard(
    tenant_id: str,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    gap_repo: ComplianceGapRepository,
) -> ComplianceDashboard:
    """Baut das Compliance-Dashboard für einen Tenant (EU AI Act / ISO 42001)."""
    systems = ai_repo.list_for_tenant(tenant_id)
    all_statuses = gap_repo.list_all_for_tenant(tenant_id)

    status_map: dict[str, list[ComplianceStatusEntry]] = {}
    for s in all_statuses:
        status_map.setdefault(s.ai_system_id, []).append(s)

    system_readiness_list: list[SystemReadiness] = []
    total_weighted_score = 0.0
    total_weight = 0.0

    for sys in systems:
        classification = cls_repo.get_for_system(tenant_id, sys.id)
        risk_level = classification.risk_level if classification else "unclassified"

        statuses = status_map.get(sys.id, [])
        if not statuses:
            system_readiness_list.append(
                SystemReadiness(
                    ai_system_id=sys.id,
                    ai_system_name=sys.name,
                    risk_level=risk_level,
                    readiness_score=0.0,
                    total_requirements=0,
                    completed=0,
                    in_progress=0,
                    not_started=0,
                )
            )
            continue

        completed = sum(1 for s in statuses if s.status == ComplianceStatus.completed)
        in_progress = sum(1 for s in statuses if s.status == ComplianceStatus.in_progress)
        not_started = sum(1 for s in statuses if s.status == ComplianceStatus.not_started)

        weighted_completed = 0.0
        weighted_total = 0.0
        for s in statuses:
            req = REQUIREMENTS_BY_ID.get(s.requirement_id)
            weight = req.weight if req else 1.0
            weighted_total += weight
            if s.status == ComplianceStatus.completed:
                weighted_completed += weight

        readiness = weighted_completed / weighted_total if weighted_total > 0 else 0.0
        total_weighted_score += weighted_completed
        total_weight += weighted_total

        system_readiness_list.append(
            SystemReadiness(
                ai_system_id=sys.id,
                ai_system_name=sys.name,
                risk_level=risk_level,
                readiness_score=round(readiness, 3),
                total_requirements=len(statuses),
                completed=completed,
                in_progress=in_progress,
                not_started=not_started,
            )
        )

    overall = round(total_weighted_score / total_weight, 3) if total_weight > 0 else 0.0
    today = date.today()
    days_remaining = max(0, (EU_AI_ACT_HIGH_RISK_DEADLINE - today).days)

    urgent_gaps: list[dict[str, str]] = []
    for sys in systems:
        classification = cls_repo.get_for_system(tenant_id, sys.id)
        if classification and classification.risk_level == "high_risk":
            for s in status_map.get(sys.id, []):
                if s.status == ComplianceStatus.not_started:
                    req = REQUIREMENTS_BY_ID.get(s.requirement_id)
                    if req:
                        urgent_gaps.append(
                            {
                                "ai_system_id": sys.id,
                                "ai_system_name": sys.name,
                                "requirement_id": req.id,
                                "requirement_name": req.name,
                                "article": req.article,
                            }
                        )
    urgent_gaps = urgent_gaps[:3]

    return ComplianceDashboard(
        tenant_id=tenant_id,
        overall_readiness=overall,
        systems=system_readiness_list,
        days_remaining=days_remaining,
        urgent_gaps=urgent_gaps,
    )


def compute_ai_compliance_overview(
    tenant_id: str,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    gap_repo: ComplianceGapRepository,
) -> AIComplianceOverview:
    """Board-fähiger Compliance-Overview aus Dashboard-Aggregation."""
    dashboard = compute_compliance_dashboard(
        tenant_id=tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
    )
    high_risk_systems = [s for s in dashboard.systems if s.risk_level == "high_risk"]
    high_risk_with_full = sum(1 for s in high_risk_systems if s.readiness_score >= 1.0)
    high_risk_with_gaps = sum(1 for s in high_risk_systems if s.not_started > 0)

    all_statuses = gap_repo.list_all_for_tenant(tenant_id)
    status_map: dict[str, list[ComplianceStatusEntry]] = {}
    for s in all_statuses:
        status_map.setdefault(s.ai_system_id, []).append(s)
    req_affected: dict[str, set[str]] = {}
    for sys in dashboard.systems:
        if sys.risk_level != "high_risk":
            continue
        for s in status_map.get(sys.ai_system_id, []):
            if s.status != ComplianceStatus.not_started:
                continue
            req = REQUIREMENTS_BY_ID.get(s.requirement_id)
            if req:
                req_affected.setdefault(req.id, set()).add(sys.ai_system_id)
    top_list: list[TopCriticalRequirement] = []
    for req_id, system_ids in sorted(
        req_affected.items(),
        key=lambda x: -len(x[1]),
    )[:5]:
        req = REQUIREMENTS_BY_ID.get(req_id)
        if req:
            top_list.append(
                TopCriticalRequirement(
                    article=req.article,
                    name=req.name,
                    affected_systems_count=len(system_ids),
                )
            )
    return AIComplianceOverview(
        tenant_id=tenant_id,
        overall_readiness=dashboard.overall_readiness,
        high_risk_systems_with_full_controls=high_risk_with_full,
        high_risk_systems_with_critical_gaps=high_risk_with_gaps,
        top_critical_requirements=top_list,
        deadline=EU_AI_ACT_HIGH_RISK_DEADLINE.isoformat(),
        days_remaining=dashboard.days_remaining,
    )
