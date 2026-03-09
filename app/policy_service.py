from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple

from app.ai_system_models import AISystem
from app.models import ComplianceAction
from app.policy_models import Policy, Severity, Violation
from app.repositories.audit import AuditRepository
from app.repositories.policies import PolicyRepository
from app.repositories.violations import ViolationRepository


class AISystemPolicyReport(NamedTuple):
    ai_system_id: str
    status: str
    violation_count: int
    action_count: int


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
    # Policies werden später genutzt; aktuell reichen die Hardcoded-Regeln
    policies: Sequence[Policy] = policy_repository.list_policies_for_tenant(tenant_id)

    core_result = evaluate_policies_for_ai_system_core(
        ai_system=ai_system,
        policies=policies,
    )

    # Idempotenz: gleiche Violation (gleiches ai_system_id, rule_id, message)
    # nicht erneut anlegen
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

    # 1) High risk + gdpr_dpia_required == False -> DPIA-Violation
    risk = getattr(ai_system, "risk_level", None)
    risk_value = getattr(risk, "value", risk)
    dpia_required = getattr(ai_system, "gdpr_dpia_required", None)

    if risk_value == "high" and dpia_required is False:
        msg = "High risk AI system without required DPIA."
        violations.append(
            Violation(
                id=None,
                tenant_id=ai_system.tenant_id,
                ai_system_id=ai_system.id,
                rule_id="high-risk-without-dpia",
                message=msg,
                description=msg,
                severity=Severity.high,
                created_at=None,
            )
        )

    # 2) High criticality + leerer owner_email -> Owner-Email-Violation
    crit = getattr(ai_system, "criticality", None)
    crit_value = getattr(crit, "value", crit)
    owner_email = getattr(ai_system, "owner_email", "")
    if crit_value == "high" and not owner_email.strip():
        msg = "High criticality AI system without valid owner email."
        violations.append(
            Violation(
                id=None,
                tenant_id=ai_system.tenant_id,
                ai_system_id=ai_system.id,
                rule_id="high-criticality-without-owner",
                message=msg,
                description=msg,
                severity=Severity.medium,
                created_at=None,
            )
        )

    # (Optional) später: deklarative Policies auswerten
    for policy in policies:
        # placeholder – aktuell keine zusätzlichen Violations
        _ = policy

    actions: list[ComplianceAction] = derive_actions(violations)
    report = _build_compliance_report(ai_system, violations, actions)

    return PolicyEvaluationResult(
        report=report,
        violations=violations,
        actions=actions,
    )


def derive_actions(violations: list[Violation]) -> list[ComplianceAction]:
    # Aktuell keine konkreten Actions; Tests erwarten nur Violations
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

