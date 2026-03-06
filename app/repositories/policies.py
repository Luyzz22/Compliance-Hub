from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import PolicyTable, RuleTable
from app.policy_models import Policy, Rule, RuleConditionType


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
        )

    @staticmethod
    def _to_rule(row: RuleTable) -> Rule:
        return Rule(
            id=row.id,
            policy_id=row.policy_id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            condition_type=RuleConditionType(row.condition_type),
        )

    def list_policies_for_tenant(self, tenant_id: str) -> list[Policy]:
        stmt = (
            select(PolicyTable)
            .where(PolicyTable.tenant_id == tenant_id)
            .order_by(PolicyTable.id)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_policy(row) for row in rows]

    def list_rules_for_tenant(self, tenant_id: str) -> list[Rule]:
        stmt = select(RuleTable).where(RuleTable.tenant_id == tenant_id).order_by(RuleTable.id)
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

        defaults = [
            (
                f"{tenant_id}-rule-high-risk-dpia",
                "High risk requires DPIA",
                "If risk_level is high, DPIA must be required.",
                RuleConditionType.high_risk_requires_dpia,
            ),
            (
                f"{tenant_id}-rule-high-criticality-owner-email",
                "High criticality requires valid owner email",
                "If criticality is high, owner_email must be present and valid.",
                RuleConditionType.high_criticality_requires_owner_email,
            ),
        ]

        for rule_id, name, description, condition_type in defaults:
            existing_rule = self._session.get(RuleTable, rule_id)
            if existing_rule is None:
                self._session.add(
                    RuleTable(
                        id=rule_id,
                        policy_id=policy_id,
                        tenant_id=tenant_id,
                        name=name,
                        description=description,
                        condition_type=condition_type.value,
                    )
                )

        self._session.commit()
