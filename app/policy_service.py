from __future__ import annotations

from collections.abc import Sequence
from typing import Any, NamedTuple

from pydantic import BaseModel

from app.ai_system_models import AISystem
from app.models import ComplianceAction
from app.policy_models import Policy, PolicyRule, PolicyRuleCondition, Severity, Violation
from app.repositories.audit import AuditRepository
from app.repositories.policies import PolicyRepository
from app.repositories.violations import ViolationRepository


class AISystemPolicyReport(NamedTuple):
    ai_system_id: str
    status: str
    violation_count: int
    action_count: int

class AISystemPolicyReportResponse(BaseModel):
    report: AISystemPolicyReport
    violations: list[Violation]

class PolicyEvaluationResult(NamedTuple):
    report: AISystemPolicyReport
    violations: list[Violation]
    actions: list[ComplianceAction]


def evaluate_policies_for_ai_system(
    tenant_id: str,
    ai_system: AISystem,
    policy_repository: PolicyRepository,
    violation_repository: ViolationRepository,
    audit_repository: AuditRepository,
    actor_type: str,
    actor_id: str,
) -> PolicyEvaluationResult:
    policies: Sequence[Policy] = policy_repository.list_policies_for_tenant(tenant_id)

    core_result = evaluate_policies_for_ai_system_core(
        ai_system=ai_system,
        policies=policies,
    )

    for violation in core_result.violations:
        existing = violation_repository.get_by_ai_system_and_rule(
            tenant_id=tenant_id,
            ai_system_id=violation.ai_system_id,
            rule_id=violation.rule_id,
            message=violation.message,
        )
        if existing is not None:
            continue

        violation_repository.create_violation(
            tenant_id=tenant_id,
            ai_system_id=violation.ai_system_id,
            rule_id=violation.rule_id,
            message=violation.message,
        )

    audit_repository.log_event(
        tenant_id=tenant_id,
        actor_type=actor_type,
        actor_id=actor_id,
        entity_type="ai_system",
        entity_id=ai_system.id,
        action="policy_evaluated",
        metadata={
            "violation_count": len(core_result.violations),
            "action_count": len(core_result.actions),
        },
    )
    audit_repository.log_event(
        tenant_id=tenant_id,
        actor_type=actor_type,
        actor_id=actor_id,
        entity_type="policy_evaluation",
        entity_id=ai_system.id,
        action="evaluated",
        metadata={
            "violations_count": len(core_result.violations),
        },
    )

    return core_result


def evaluate_policies_for_ai_system_core(
    ai_system: AISystem,
    policies: Sequence[Policy],
) -> PolicyEvaluationResult:
    violations: list[Violation] = []

    for policy in policies:
        for rule in policy.rules:
            if _matches_rule(ai_system, rule):
                violations.append(
                    Violation(
                        id=None,
                        tenant_id=ai_system.tenant_id,
                        ai_system_id=ai_system.id,
                        rule_id=rule.id,
                        message=rule.message,
                        description=rule.description,
                        severity=rule.severity,
                        created_at=None,
                    )
                )

    actions: list[ComplianceAction] = derive_actions(violations)
    report = _build_compliance_report(ai_system, violations, actions)

    return PolicyEvaluationResult(
        report=report,
        violations=violations,
        actions=actions,
    )


def _matches_rule(ai_system: AISystem, rule: PolicyRule) -> bool:
    return all(_matches_condition(ai_system, condition) for condition in rule.conditions)


def _matches_condition(ai_system: AISystem, condition: PolicyRuleCondition) -> bool:
    value = _read_field_value(ai_system, condition.field_path)
    if condition.operator == "equals":
        return value == condition.expected
    if condition.operator == "is_blank":
        if not condition.expected:
            return False
        return not isinstance(value, str) or not value.strip()
    return False


def _read_field_value(ai_system: AISystem, field_path: str) -> Any:
    value = getattr(ai_system, field_path, None)
    return getattr(value, "value", value)


def derive_actions(violations: list[Violation]) -> list[ComplianceAction]:
    return []


def _build_compliance_report(
    ai_system: AISystem,
    violations: list[Violation],
    actions: list[ComplianceAction],
) -> AISystemPolicyReport:
    if not violations:
        status = "compliant"
    elif any(v.severity == Severity.high for v in violations):
        status = "non_compliant"
    else:
        status = "partially_compliant"

    return AISystemPolicyReport(
        ai_system_id=ai_system.id,
        status=status,
        violation_count=len(violations),
        action_count=len(actions),
    )

