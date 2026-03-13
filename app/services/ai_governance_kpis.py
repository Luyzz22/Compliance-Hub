from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from app.ai_governance_models import AIBoardKpiSummary, AIGovernanceKpiSummary
from app.datetime_compat import UTC
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditRepository
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
) -> AIGovernanceKpiSummary:
    # Datenbasis aus Repositories
    ai_systems = ai_system_repository.list_for_tenant(tenant_id)
    violations = violation_repository.list_violations_for_tenant(tenant_id)
    events = audit_repository.list_events_for_tenant(tenant_id, limit=500)
    policies = policy_repository.list_policies_for_tenant(tenant_id)

    # Basiszahlen
    ai_systems_total = len(ai_systems)
    ai_systems_with_owner = sum(
        1 for s in ai_systems if s.owner_email and s.owner_email.strip()
    )

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
    )



def compute_ai_board_kpis(
    tenant_id: str,
    ai_system_repository: AISystemRepository,
    violation_repository: ViolationRepository,
) -> AIBoardKpiSummary:
    ai_systems = ai_system_repository.list_for_tenant(tenant_id)
    violations = violation_repository.list_violations_for_tenant(tenant_id)

    return AIBoardKpiSummary(
        tenant_id=tenant_id,
        ai_systems_total=len(ai_systems),
        active_ai_systems=sum(1 for s in ai_systems if s.status == "active"),
        high_risk_systems=sum(1 for s in ai_systems if s.risk_level == "high"),
        open_policy_violations=len(violations),
    )
