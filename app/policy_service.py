from __future__ import annotations

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.ai_system_models import AISystem, AISystemCriticality, AISystemRiskLevel
from app.policy_models import RuleConditionType, Violation
from app.repositories.policies import PolicyRepository, ViolationRepository


class PolicyEvaluationService:
    def __init__(
        self, policy_repository: PolicyRepository, violation_repository: ViolationRepository
    ) -> None:
        self._policy_repository = policy_repository
        self._violation_repository = violation_repository

    def evaluate_policies_for_ai_system(
        self, tenant_id: str, ai_system: AISystem
    ) -> list[Violation]:
        self._policy_repository.ensure_default_policy_and_rules(tenant_id)

        active_policy_ids = {
            policy.id
            for policy in self._policy_repository.list_policies_for_tenant(tenant_id)
            if policy.active
        }
        rules = [
            rule
            for rule in self._policy_repository.list_rules_for_tenant(tenant_id)
            if rule.policy_id in active_policy_ids
        ]

        violations: list[Violation] = []
        for rule in rules:
            message = self._evaluate_rule(ai_system=ai_system, condition_type=rule.condition_type)
            if message is None:
                continue
            violations.append(
                self._violation_repository.create_violation(
                    tenant_id=tenant_id,
                    ai_system_id=ai_system.id,
                    rule_id=rule.id,
                    message=message,
                )
            )
        return violations

    def _evaluate_rule(self, ai_system: AISystem, condition_type: RuleConditionType) -> str | None:
        if (
            condition_type == RuleConditionType.high_risk_requires_dpia
            and ai_system.risk_level == AISystemRiskLevel.high
            and not ai_system.gdpr_dpia_required
        ):
            return "AISystem with high risk level requires gdpr_dpia_required=true."

        if (
            condition_type == RuleConditionType.high_criticality_requires_owner_email
            and ai_system.criticality == AISystemCriticality.high
            and not self._is_valid_email(ai_system.owner_email)
        ):
            return "AISystem with high criticality requires a valid owner_email."

        return None

    @staticmethod
    def _is_valid_email(email: str | None) -> bool:
        if email is None or not email.strip():
            return False
        try:
            TypeAdapter(EmailStr).validate_python(email)
        except ValidationError:
            return False
        except ValueError:
            return False
        return True
