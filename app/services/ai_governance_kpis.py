from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from app.ai_governance_models import AIBoardKpiSummary, AIGovernanceKpiSummary
from app.datetime_compat import UTC
from app.repositories.ai_systems import AISystemRepository
from app.repositories.ai_inventory import AISystemInventoryRepository
from app.repositories.audit import AuditRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.policies import PolicyRepository
from app.repositories.violations import ViolationRepository


def _as_utc(dt: datetime) -> datetime:
    """
    Normalisiert alle Timestamps auf UTC, damit Vergleiche in KPIs
    (z.B. „Events in den letzten 30 Tagen“) in CI und Produktion
    konsistent und timezone-safe laufen.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _count_audit_events_last_30_days(events: Iterable) -> int:
    """
    Zählt Audit-Events innerhalb der letzten 30 Tage.
    Nutzt ausschließlich offset-aware UTC-Zeiten, um TypeError
    („naive vs aware“) zu vermeiden.
    """
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    return sum(1 for event in events if _as_utc(event.timestamp) >= thirty_days_ago)


def compute_ai_governance_kpis(
    tenant_id: str,
    ai_system_repository: AISystemRepository,
    policy_repository: PolicyRepository,
    violation_repository: ViolationRepository,
    audit_repository: AuditRepository,
    nis2_kritis_kpi_repository: Nis2KritisKpiRepository,
) -> AIGovernanceKpiSummary:
    # Datenbasis aus Repositories
    ai_systems = ai_system_repository.list_for_tenant(tenant_id)
    violations = violation_repository.list_violations_for_tenant(tenant_id)
    events = audit_repository.list_events_for_tenant(tenant_id, limit=500)
    policies = policy_repository.list_policies_for_tenant(tenant_id)

    # Basiszahlen
    ai_systems_total = len(ai_systems)
    ai_systems_with_owner = sum(1 for s in ai_systems if s.owner_email and s.owner_email.strip())

    # High-Risk-Fokus (EU AI Act / ISO 42001 / ISO 27001 Kontext)
    high_risk_systems = [s for s in ai_systems if s.risk_level == "high"]
    high_risk_total = len(high_risk_systems)
    high_risk_with_dpia = sum(1 for s in high_risk_systems if s.gdpr_dpia_required)

    # Audit-Events der letzten 30 Tage (timezone-safe)
    audit_events_last_30_days = _count_audit_events_last_30_days(events)

    # KPI-Gewichtung – Board-ready Score (0..1)
    # 0.4 Owner-Coverage, 0.4 DPIA-Coverage für High-Risk, 0.2 Strafterm für offene Violations
    owner_ratio = ai_systems_with_owner / ai_systems_total if ai_systems_total else 1.0
    dpia_ratio = high_risk_with_dpia / high_risk_total if high_risk_total else 1.0
    violation_penalty = min(1.0, len(violations) / max(ai_systems_total, 1))
    weighted_score = (0.4 * owner_ratio) + (0.4 * dpia_ratio) + (0.2 * (1 - violation_penalty))
    governance_maturity_score = max(0.0, min(1.0, weighted_score))

    # Policy-/Register-Indikatoren (NIS2 / ISO 27001 Annex A / ISO 42001)
    policy_ids = {policy.id for policy in policies}
    has_documented_ai_policy = any("policy" in policy_id for policy_id in policy_ids)
    has_ai_risk_register = any(system.has_supplier_risk_register for system in ai_systems)

    mean_nis2, nis2_coverage = nis2_kritis_kpi_repository.aggregate_for_tenant(tenant_id)
    mean_rounded = round(mean_nis2, 2) if mean_nis2 is not None else None

    return AIGovernanceKpiSummary(
        tenant_id=tenant_id,
        governance_maturity_score=round(governance_maturity_score, 3),
        ai_systems_with_owner=ai_systems_with_owner,
        ai_systems_total=ai_systems_total,
        high_risk_with_dpia=high_risk_with_dpia,
        high_risk_total=high_risk_total,
        policy_violations_open=len(violations),
        audit_events_last_30_days=audit_events_last_30_days,
        has_documented_ai_policy=has_documented_ai_policy,
        has_ai_risk_register=has_ai_risk_register,
        nis2_kritis_kpi_mean_percent=mean_rounded,
        nis2_kritis_systems_full_coverage_ratio=round(nis2_coverage, 4),
    )


def compute_ai_board_kpis(
    tenant_id: str,
    ai_system_repository: AISystemRepository,
    violation_repository: ViolationRepository,
    nis2_kritis_kpi_repository: Nis2KritisKpiRepository,
    inventory_repository: AISystemInventoryRepository | None = None,
) -> AIBoardKpiSummary:
    ai_systems = ai_system_repository.list_for_tenant(tenant_id)
    violations = violation_repository.list_violations_for_tenant(tenant_id)

    total_systems = len(ai_systems)
    active_systems = sum(1 for s in ai_systems if s.status == "active")
    high_risk_systems = sum(1 for s in ai_systems if s.risk_level == "high")
    open_violations = len(violations)

    high_risk_systems_without_dpia = sum(
        1 for s in ai_systems if s.risk_level == "high" and not s.gdpr_dpia_required
    )
    critical_systems_without_owner = sum(
        1
        for s in ai_systems
        if s.criticality in ("high", "very_high") and not (s.owner_email and s.owner_email.strip())
    )
    nis2_control_gaps = sum(
        (1 if not s.has_incident_runbook else 0)
        + (1 if not s.has_backup_runbook else 0)
        + (1 if not s.has_supplier_risk_register else 0)
        for s in ai_systems
    )

    owner_ratio = (
        sum(1 for s in ai_systems if s.owner_email and s.owner_email.strip()) / total_systems
        if total_systems
        else 1.0
    )
    dpia_ratio = (
        sum(1 for s in ai_systems if s.risk_level == "high" and s.gdpr_dpia_required)
        / high_risk_systems
        if high_risk_systems
        else 1.0
    )
    runbook_ratio = (
        sum(
            1
            for s in ai_systems
            if s.has_incident_runbook and s.has_backup_runbook and s.has_supplier_risk_register
        )
        / total_systems
        if total_systems
        else 1.0
    )
    # NIS2 Art. 21 – Incident/BCM: Anteil Systeme mit Incident- und Backup-Runbook
    nis2_incident_readiness_ratio = (
        sum(1 for s in ai_systems if s.has_incident_runbook and s.has_backup_runbook)
        / total_systems
        if total_systems
        else 1.0
    )
    # NIS2 Art. 24 – Supply Chain: Anteil Systeme mit Lieferanten-Risiko-Register
    nis2_supplier_risk_coverage_ratio = (
        sum(1 for s in ai_systems if s.has_supplier_risk_register) / total_systems
        if total_systems
        else 1.0
    )
    violation_penalty = min(1.0, open_violations / max(total_systems, 1))
    # ISO 42001 – AI-MS-Reife: Kontext, Führung, Risikobewertung, Betrieb, Verbesserung.
    # Für die operative Fähigkeit werden hier Incident-Readiness (Incident- + Backup-Runbook)
    # und Lieferanten-Risikomanagement getrennt gewichtet.
    supplier_ratio = nis2_supplier_risk_coverage_ratio
    iso42001_governance_score = max(
        0.0,
        min(
            1.0,
            0.2 * owner_ratio
            + 0.2 * dpia_ratio
            + 0.25 * nis2_incident_readiness_ratio
            + 0.2 * supplier_ratio
            + 0.15 * (1 - violation_penalty),
        ),
    )
    board_maturity_score = max(
        0.0,
        min(
            1.0,
            0.35 * owner_ratio
            + 0.35 * dpia_ratio
            + 0.2 * runbook_ratio
            + 0.1 * (1 - violation_penalty),
        ),
    )
    compliance_coverage_score = dpia_ratio
    risk_governance_score = owner_ratio
    operational_resilience_score = runbook_ratio
    responsible_ai_score = 1.0 - violation_penalty

    mean_nis2, nis2_coverage = nis2_kritis_kpi_repository.aggregate_for_tenant(tenant_id)
    mean_rounded = round(mean_nis2, 2) if mean_nis2 is not None else None
    posture = (
        inventory_repository.posture_summary(tenant_id, total_systems)
        if inventory_repository is not None
        else None
    )

    return AIBoardKpiSummary(
        tenant_id=tenant_id,
        ai_systems_total=total_systems,
        active_ai_systems=active_systems,
        high_risk_systems=high_risk_systems,
        open_policy_violations=open_violations,
        board_maturity_score=round(board_maturity_score, 3),
        compliance_coverage_score=round(compliance_coverage_score, 3),
        risk_governance_score=round(risk_governance_score, 3),
        operational_resilience_score=round(operational_resilience_score, 3),
        responsible_ai_score=round(responsible_ai_score, 3),
        high_risk_systems_without_dpia=high_risk_systems_without_dpia,
        critical_systems_without_owner=critical_systems_without_owner,
        nis2_control_gaps=nis2_control_gaps,
        nis2_incident_readiness_ratio=round(nis2_incident_readiness_ratio, 3),
        nis2_supplier_risk_coverage_ratio=round(nis2_supplier_risk_coverage_ratio, 3),
        iso42001_governance_score=round(iso42001_governance_score, 3),
        score_change_vs_last_quarter=0.0,
        incidents_last_quarter=0,
        complaints_last_quarter=0,
        nis2_kritis_kpi_mean_percent=mean_rounded,
        nis2_kritis_systems_full_coverage_ratio=round(nis2_coverage, 4),
        ki_register_registered=posture.registered if posture else 0,
        ki_register_planned=posture.planned if posture else 0,
        ki_register_partial=posture.partial if posture else 0,
        ki_register_unknown=posture.unknown if posture else total_systems,
    )
