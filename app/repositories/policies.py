from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import PolicyTable, RuleTable
from app.policy_models import (
    Policy,
    PolicyRuleCondition,
    Rule,
    RuleConditionType,
    Severity,
)


class PolicyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_policy(row: PolicyTable) -> Policy:
        return Policy(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            active=row.active,
            rules=[],
        )

    @staticmethod
    def _to_rule(row: RuleTable) -> Rule:
        condition_type = RuleConditionType(row.condition_type)

        if condition_type == RuleConditionType.high_risk_requires_dpia:
            return Rule(
                id=row.id,
                policy_id=row.policy_id,
                tenant_id=row.tenant_id,
                name=row.name,
                description=row.description or "High risk requires DPIA",
                severity=Severity.high,
                message="High risk AI system without required DPIA.",
                conditions=[
                    PolicyRuleCondition(field_path="risk_level", expected="high"),
                    PolicyRuleCondition(field_path="gdpr_dpia_required", expected=False),
                ],
            )

        if condition_type == RuleConditionType.high_criticality_requires_owner_email:
            return Rule(
                id=row.id,
                policy_id=row.policy_id,
                tenant_id=row.tenant_id,
                name=row.name,
                description=(
                    row.description or "High criticality requires valid owner email"
                ),
                severity=Severity.medium,
                message="High criticality AI system without valid owner email.",
                conditions=[
                    PolicyRuleCondition(field_path="criticality", expected="high"),
                    PolicyRuleCondition(
                        field_path="owner_email",
                        expected=True,
                        operator="is_blank",
                    ),
                ],
            )

        raise ValueError(f"Unsupported rule condition type: {row.condition_type}")

    def list_policies_for_tenant(self, tenant_id: str) -> list[Policy]:
        # Für diesen Schritt: nur eingebaute Policies, damit Verhalten den alten
        # Hardcoded-Regeln entspricht.
        return self._builtin_policies_for_tenant(tenant_id)

    def _builtin_policies_for_tenant(self, tenant_id: str) -> list[Policy]:
        return [
            Policy(
                id="builtin-high-risk-dpia",
                tenant_id=tenant_id,
                name="Builtin: High risk requires DPIA",
                description="Flags high-risk AI systems where DPIA is not required.",
                rules=[
                    Rule(
                        id="high-risk-without-dpia",
                        policy_id="builtin-high-risk-dpia",
                        tenant_id=tenant_id,
                        name="High risk requires DPIA",
                        description=(
                            "If risk_level is high, gdpr_dpia_required must not be false."
                        ),
                        severity=Severity.high,
                        message="High risk AI system without required DPIA.",
                        conditions=[
                            PolicyRuleCondition(
                                field_path="risk_level",
                                expected="high",
                            ),
                            PolicyRuleCondition(
                                field_path="gdpr_dpia_required",
                                expected=False,
                            ),
                        ],
                    )
                ],
            ),
            Policy(
                id="builtin-criticality-owner",
                tenant_id=tenant_id,
                name="Builtin: High criticality requires owner",
                description="Flags high-criticality AI systems without owner email.",
                rules=[
                    Rule(
                        id="high-criticality-without-owner",
                        policy_id="builtin-criticality-owner",
                        tenant_id=tenant_id,
                        name="High criticality requires valid owner email",
                        description=(
                            "If criticality is high, owner_email must be present."
                        ),
                        severity=Severity.medium,
                        message="High criticality AI system without valid owner email.",
                        conditions=[
                            PolicyRuleCondition(
                                field_path="criticality",
                                expected="high",
                            ),
                            PolicyRuleCondition(
                                field_path="owner_email",
                                expected=True,
                                operator="is_blank",
                            ),
                        ],
                    )
                ],
            ),
        ]

    def list_rules_for_tenant(self, tenant_id: str) -> list[Rule]:
        stmt = (
            select(RuleTable)
            .where(RuleTable.tenant_id == tenant_id)
            .order_by(RuleTable.id)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_rule(row) for row in rows]

    def ensure_default_policy_rules(self, tenant_id: str) -> None:
        policy_id = f"{tenant_id}-default-policy"
        existing_policy = self._session.get(PolicyTable, policy_id)
        if existing_policy is None:
            self._session.add(
                PolicyTable(
                    id=policy_id,
                    tenant_id=tenant_id,
                    name="Default AI Compliance Policy",
                    description="Default baseline compliance checks",
                    active=True,
                )
            )
        # Default-Regeln werden aktuell nicht benötigt; Implementierung folgt bei Bedarf.

