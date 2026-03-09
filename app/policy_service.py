from __future__ import annotations

from app.ai_system_models import AISystem, AISystemCriticality, AISystemRiskLevel
from app.policy_models import Rule, RuleConditionType, Violation
from app.repositories.audit import AuditRepository
from app.repositories.policies import PolicyRepository
from app.repositories.violations import ViolationRepository


def _is_valid_email(value: str) -> bool:
    return bool(value and "@" in value and "." in value.split("@")[-1])


def _evaluate_rule(ai_system: AISystem, rule: Rule) -> str | None:
    if rule.condition_type == RuleConditionType.high_risk_requires_dpia:
        if ai_system.risk_level == AISystemRiskLevel.high and not ai_system.gdpr_dpia_required:
            return "High risk AI system requires GDPR DPIA to be set to true."
        return None

    if rule.condition_type == RuleConditionType.high_criticality_requires_owner_email:
        owner_email = str(ai_system.owner_email) if ai_system.owner_email is not None else ""
        if ai_system.criticality == AISystemCriticality.high and not _is_valid_email(owner_email):
            return "High criticality AI system requires a valid owner email."
        return None

    return None


def evaluate_policies_for_ai_system(
    tenant_id: str,
    ai_system: AISystem,
    policy_repository: PolicyRepository,
    violation_repository: ViolationRepository,
    audit_repository: AuditRepository | None = None,
    actor_type: str = "api_key",
    actor_id: str | None = None,
) -> list[Violation]:
    policy_repository.ensure_default_policy_rules(tenant_id)

    active_policy_ids = {
        policy.id
        for policy in policy_repository.list_policies_for_tenant(tenant_id)
        if policy.active
    }
    tenant_rules = [
        rule
        for rule in policy_repository.list_rules_for_tenant(tenant_id)
        if rule.policy_id in active_policy_ids
    ]

    violations: list[Violation] = []
    for rule in tenant_rules:
        message = _evaluate_rule(ai_system, rule)
        if message is None:
            continue

        existing = violation_repository.get_by_ai_system_and_rule(
            tenant_id=tenant_id,
            ai_system_id=ai_system.id,
            rule_id=rule.id,
            message=message,
        )
        if existing is not None:
            violations.append(existing)
            continue

        created = violation_repository.create_violation(
            tenant_id=tenant_id,
            ai_system_id=ai_system.id,
            rule_id=rule.id,
            message=message,
        )
        violations.append(created)


    if audit_repository is not None:
        audit_repository.log_event(
            tenant_id=tenant_id,
            actor_type=actor_type,
            actor_id=actor_id,
            entity_type="policy_evaluation",
            entity_id=ai_system.id,
            action="policies_evaluated",
            metadata={
                "violations_count": len(violations),
                "ai_system_id": ai_system.id,
            },
        )

    return violations
