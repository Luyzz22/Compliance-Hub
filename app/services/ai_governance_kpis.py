from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.ai_governance_models import AIGovernanceKpiSummary
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditRepository
from app.repositories.policies import PolicyRepository
from app.repositories.violations import ViolationRepository


def compute_ai_governance_kpis(
    tenant_id: str,
    ai_system_repository: AISystemRepository,
    policy_repository: PolicyRepository,
    violation_repository: ViolationRepository,
    audit_repository: AuditRepository,
) -> AIGovernanceKpiSummary:
    ai_systems = ai_system_repository.list_for_tenant(tenant_id)
    violations = violation_repository.list_violations_for_tenant(tenant_id)
    events = audit_repository.list_events_for_tenant(tenant_id, limit=500)
    policies = policy_repository.list_policies_for_tenant(tenant_id)

    ai_systems_total = len(ai_systems)
    ai_systems_with_owner = sum(1 for s in ai_systems if s.owner_email and s.owner_email.strip())

    high_risk_systems = [s for s in ai_systems if s.risk_level == "high"]
    high_risk_total = len(high_risk_systems)
    high_risk_with_dpia = sum(1 for s in high_risk_systems if s.gdpr_dpia_required)

    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    audit_events_last_30_days = sum(1 for event in events if event.timestamp >= thirty_days_ago)

    owner_ratio = ai_systems_with_owner / ai_systems_total if ai_systems_total else 1.0
    dpia_ratio = high_risk_with_dpia / high_risk_total if high_risk_total else 1.0
    violation_penalty = min(1.0, len(violations) / max(ai_systems_total, 1))
    weighted_score = (0.4 * owner_ratio) + (0.4 * dpia_ratio) + (0.2 * (1 - violation_penalty))
    governance_maturity_score = max(0.0, min(1.0, weighted_score))

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
