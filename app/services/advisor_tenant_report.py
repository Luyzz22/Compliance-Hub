from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.advisor_models import (
    AdvisorTenantReport,
    TenantReportCriticalRequirementItem,
)
from app.config.nis2_kritis_board_alert_thresholds import NIS2_KRITIS_OT_IT_ALERT_THRESHOLD_PCT
from app.nis2_kritis_models import Nis2KritisKpiType
from app.repositories.advisor_tenants import AdvisorTenantLink
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_gap import ComplianceGapRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.violations import ViolationRepository
from app.services.advisor_tenant_report_risiko import build_tenant_report_risiko_fields
from app.services.ai_governance_kpis import compute_ai_board_kpis
from app.services.eu_ai_act_readiness import compute_eu_ai_act_readiness_overview
from app.services.setup_status import compute_tenant_setup_status
from app.setup_models import TenantSetupStatus


def _open_setup_labels(status: TenantSetupStatus) -> list[str]:
    """Reihenfolge wie Guided-Setup-Wizard."""
    labels: list[tuple[bool, str]] = [
        (status.ai_inventory_completed, "KI-Inventar"),
        (status.classification_completed, "Klassifikation (EU AI Act)"),
        (status.nis2_kpis_seeded, "NIS2-/KRITIS-KPIs"),
        (status.policies_published, "Kern-Policies"),
        (status.actions_defined, "Governance-Actions"),
        (status.evidence_attached, "Evidenzen"),
        (status.eu_ai_act_readiness_baseline_created, "Readiness-Baseline"),
    ]
    return [text for ok, text in labels if not ok]


def build_advisor_tenant_report(
    session: Session,
    tenant_id: str,
    *,
    link: AdvisorTenantLink,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    gap_repo: ComplianceGapRepository,
    nis2_repo: Nis2KritisKpiRepository,
    violation_repo: ViolationRepository,
    action_repo: AIGovernanceActionRepository,
    incident_repo: IncidentRepository,
) -> AdvisorTenantReport:
    """
    Aggregiert einen Mandanten-Steckbrief ausschließlich über tenant-gefilterte Services/Repos.
    """
    if link.tenant_id != tenant_id:
        raise ValueError("Advisor link tenant_id mismatch")

    board = compute_ai_board_kpis(
        tenant_id=tenant_id,
        ai_system_repository=ai_repo,
        violation_repository=violation_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    readiness = compute_eu_ai_act_readiness_overview(
        tenant_id=tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        nis2_repo=nis2_repo,
        action_repo=action_repo,
    )
    setup = compute_tenant_setup_status(session, tenant_id)

    by_type = nis2_repo.mean_percent_by_kpi_type(tenant_id)
    ot_it = by_type.get(Nis2KritisKpiType.OT_IT_SEGREGATION)

    critical_focus = nis2_repo.count_focus_systems_ot_it_below(
        tenant_id,
        threshold_percent=NIS2_KRITIS_OT_IT_ALERT_THRESHOLD_PCT,
    )
    open_actions = action_repo.count_open_or_in_progress(tenant_id)
    overdue = action_repo.count_overdue_open_or_in_progress(tenant_id)

    top3 = [
        TenantReportCriticalRequirementItem(
            code=c.code,
            name=c.name,
            affected_systems_count=c.affected_systems_count,
        )
        for c in sorted(
            readiness.critical_requirements,
            key=lambda x: (x.priority, -x.affected_systems_count),
        )[:3]
    ]

    display_name = (link.tenant_display_name or "").strip() or tenant_id

    risiko = build_tenant_report_risiko_fields(
        session,
        tenant_id,
        incident_repo,
        eu_ai_act_readiness_score=round(readiness.overall_readiness, 4),
        nis2_incident_readiness_percent=round(board.nis2_incident_readiness_ratio * 100.0, 1),
    )

    return AdvisorTenantReport(
        tenant_id=tenant_id,
        tenant_name=display_name,
        industry=link.industry,
        country=link.country,
        generated_at_utc=datetime.now(UTC),
        ai_systems_total=board.ai_systems_total,
        high_risk_systems_count=board.high_risk_systems,
        high_risk_with_full_controls_count=readiness.high_risk_systems_essential_complete,
        eu_ai_act_readiness_score=round(readiness.overall_readiness, 4),
        eu_ai_act_deadline=readiness.deadline,
        eu_ai_act_days_remaining=readiness.days_remaining,
        nis2_incident_readiness_percent=round(board.nis2_incident_readiness_ratio * 100, 1),
        nis2_supplier_risk_coverage_percent=round(board.nis2_supplier_risk_coverage_ratio * 100, 1),
        nis2_ot_it_segregation_mean_percent=(round(ot_it, 1) if ot_it is not None else None),
        nis2_critical_focus_systems_count=critical_focus,
        governance_open_actions_count=open_actions,
        governance_overdue_actions_count=overdue,
        top_critical_requirements=top3,
        setup_completed_steps=setup.completed_steps,
        setup_total_steps=setup.total_steps,
        setup_open_step_labels=_open_setup_labels(setup),
        **risiko,
    )
