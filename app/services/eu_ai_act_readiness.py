"""EU-AI-Act-Readiness (Stichtag High-Risk) mit Gap-Heuristik und Maßnahmen-Vorschlägen."""

from __future__ import annotations

from app.ai_governance_action_models import GovernanceActionStatus
from app.compliance_gap_models import ComplianceStatus, ComplianceStatusEntry
from app.eu_ai_act_readiness_models import (
    EUAIActReadinessOverview,
    ReadinessCriticalRequirement,
    ReadinessRequirementTraffic,
    SuggestedGovernanceAction,
)
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_gap import ComplianceGapRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.services.compliance_dashboard import compute_ai_compliance_overview

ART12_ID = "art12_logging"


def _statuses_map(
    tenant_id: str,
    gap_repo: ComplianceGapRepository,
) -> dict[str, list[ComplianceStatusEntry]]:
    all_s = gap_repo.list_all_for_tenant(tenant_id)
    m: dict[str, list[ComplianceStatusEntry]] = {}
    for s in all_s:
        m.setdefault(s.ai_system_id, []).append(s)
    return m


def _essential_controls_ok(
    system_id: str,
    *,
    gdpr_dpia_required: bool,
    has_incident_runbook: bool,
    has_backup_runbook: bool,
    has_supplier_risk_register: bool,
    statuses: list[ComplianceStatusEntry],
) -> bool:
    if not gdpr_dpia_required:
        return False
    if not (has_incident_runbook and has_backup_runbook):
        return False
    if not has_supplier_risk_register:
        return False
    art12 = next((s for s in statuses if s.requirement_id == ART12_ID), None)
    return art12 is not None and art12.status == ComplianceStatus.completed


def _traffic_for_count(n: int) -> ReadinessRequirementTraffic:
    if n >= 3:
        return ReadinessRequirementTraffic.red
    if n >= 2:
        return ReadinessRequirementTraffic.amber
    return ReadinessRequirementTraffic.green


def _build_suggested(
    tenant_id: str,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    smap: dict[str, list[ComplianceStatusEntry]],
) -> list[SuggestedGovernanceAction]:
    suggestions: list[SuggestedGovernanceAction] = []
    systems = ai_repo.list_for_tenant(tenant_id)
    for sys in systems:
        cl = cls_repo.get_for_system(tenant_id, sys.id)
        if cl is None or cl.risk_level != "high_risk":
            continue
        st = smap.get(sys.id, [])
        if _essential_controls_ok(
            sys.id,
            gdpr_dpia_required=sys.gdpr_dpia_required,
            has_incident_runbook=sys.has_incident_runbook,
            has_backup_runbook=sys.has_backup_runbook,
            has_supplier_risk_register=sys.has_supplier_risk_register,
            statuses=st,
        ):
            continue
        if not sys.gdpr_dpia_required:
            suggestions.append(
                SuggestedGovernanceAction(
                    related_requirement="EU AI Act / DSGVO – DPIA",
                    title=f"DPIA für High-Risk-System „{sys.name}“ abschließen",
                    rationale="High-Risk-KI erfordert dokumentierte Datenschutz-Folgenabschätzung.",
                    suggested_priority=1,
                )
            )
        if not (sys.has_incident_runbook and sys.has_backup_runbook):
            suggestions.append(
                SuggestedGovernanceAction(
                    related_requirement="NIS2 Art. 21 / ISO 42001 – Incident",
                    title=f"Incident- und Backup-Runbook für „{sys.name}“",
                    rationale="Operative Resilienz und Nachweisbarkeit für NIS2/KRITIS.",
                    suggested_priority=2,
                )
            )
        if not sys.has_supplier_risk_register:
            suggestions.append(
                SuggestedGovernanceAction(
                    related_requirement="NIS2 Art. 24 – Supplier Risk",
                    title=f"Lieferanten-Risikoregister für „{sys.name}“",
                    rationale="Supply-Chain-Transparenz für kritische KI-Abhängigkeiten.",
                    suggested_priority=2,
                )
            )
        art12 = next((s for s in st if s.requirement_id == ART12_ID), None)
        if art12 is None or art12.status != ComplianceStatus.completed:
            suggestions.append(
                SuggestedGovernanceAction(
                    related_requirement="EU AI Act Art. 12 – Logging",
                    title=f"Monitoring/Logging-Anforderungen für „{sys.name}“ umsetzen",
                    rationale="Aufzeichnungspflicht für High-Risk-KI im Betrieb.",
                    suggested_priority=3,
                )
            )
    return suggestions[:15]


def compute_eu_ai_act_readiness_overview(
    tenant_id: str,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    gap_repo: ComplianceGapRepository,
    nis2_repo: Nis2KritisKpiRepository,
    action_repo: AIGovernanceActionRepository,
) -> EUAIActReadinessOverview:
    base = compute_ai_compliance_overview(
        tenant_id=tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    smap = _statuses_map(tenant_id, gap_repo)
    complete = 0
    incomplete = 0
    for sys in ai_repo.list_for_tenant(tenant_id):
        cl = cls_repo.get_for_system(tenant_id, sys.id)
        if cl is None or cl.risk_level != "high_risk":
            continue
        ok = _essential_controls_ok(
            sys.id,
            gdpr_dpia_required=sys.gdpr_dpia_required,
            has_incident_runbook=sys.has_incident_runbook,
            has_backup_runbook=sys.has_backup_runbook,
            has_supplier_risk_register=sys.has_supplier_risk_register,
            statuses=smap.get(sys.id, []),
        )
        if ok:
            complete += 1
        else:
            incomplete += 1

    critical: list[ReadinessCriticalRequirement] = []
    sorted_top = sorted(
        base.top_critical_requirements,
        key=lambda r: -r.affected_systems_count,
    )
    for i, tr in enumerate(sorted_top[:8]):
        critical.append(
            ReadinessCriticalRequirement(
                code=tr.article,
                name=tr.name,
                affected_systems_count=tr.affected_systems_count,
                traffic=_traffic_for_count(tr.affected_systems_count),
                priority=min(5, i + 1),
            )
        )

    open_actions = action_repo.list_for_tenant(
        tenant_id,
        limit=50,
    )
    open_only = [
        a
        for a in open_actions
        if a.status in (GovernanceActionStatus.open, GovernanceActionStatus.in_progress)
    ][:20]

    suggested = _build_suggested(tenant_id, ai_repo, cls_repo, smap)

    return EUAIActReadinessOverview(
        tenant_id=tenant_id,
        deadline=base.deadline,
        days_remaining=base.days_remaining,
        overall_readiness=base.overall_readiness,
        high_risk_systems_essential_complete=complete,
        high_risk_systems_essential_incomplete=incomplete,
        critical_requirements=critical,
        suggested_actions=suggested,
        open_governance_actions=open_only,
    )
