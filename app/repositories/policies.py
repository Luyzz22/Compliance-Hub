from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import PolicyTable, RuleTable, ViolationTable
from app.policy_models import Policy, Rule, RuleConditionType, Violation


class PolicyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _policy_to_domain(row: PolicyTable) -> Policy:
        return Policy(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            active=row.active,
        )

    @staticmethod
    def _rule_to_domain(row: RuleTable) -> Rule:
        return Rule(
            id=row.id,
            policy_id=row.policy_id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            condition_type=RuleConditionType(row.condition_type),
        )

    def ensure_default_policy_and_rules(self, tenant_id: str) -> None:
        policy_id = f"default-policy-{tenant_id}"
        policy = self._session.execute(
            select(PolicyTable).where(
                PolicyTable.id == policy_id, PolicyTable.tenant_id == tenant_id
            )
        ).scalar_one_or_none()

        if policy is None:
            self._session.add(
                PolicyTable(
                    id=policy_id,
                    tenant_id=tenant_id,
                    name="Default AI Compliance Policy",
                    description="Default policy for baseline AI system compliance checks.",
                    active=True,
                )
            )

        default_rules: list[tuple[str, str, str]] = [
            (
                f"rule-high-risk-dpia-{tenant_id}",
                "High risk requires DPIA",
                RuleConditionType.high_risk_requires_dpia.value,
            ),
            (
                f"rule-high-criticality-owner-email-{tenant_id}",
                "High criticality requires owner email",
                RuleConditionType.high_criticality_requires_owner_email.value,
            ),
        ]

        for rule_id, rule_name, condition in default_rules:
            existing_rule = self._session.execute(
                select(RuleTable).where(RuleTable.id == rule_id, RuleTable.tenant_id == tenant_id)
            ).scalar_one_or_none()
            if existing_rule is None:
                self._session.add(
                    RuleTable(
                        id=rule_id,
                        policy_id=policy_id,
                        tenant_id=tenant_id,
                        name=rule_name,
                        description=f"Auto-generated default rule for {condition}.",
                        condition_type=condition,
                    )
                )

        self._session.commit()

    def list_policies_for_tenant(self, tenant_id: str) -> list[Policy]:
        stmt = (
            select(PolicyTable)
            .where(PolicyTable.tenant_id == tenant_id)
            .order_by(PolicyTable.name.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._policy_to_domain(row) for row in rows]

    def list_rules_for_tenant(self, tenant_id: str) -> list[Rule]:
        stmt = (
            select(RuleTable).where(RuleTable.tenant_id == tenant_id).order_by(RuleTable.name.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._rule_to_domain(row) for row in rows]


class ViolationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: ViolationTable) -> Violation:
        return Violation(
            id=row.id,
            tenant_id=row.tenant_id,
            ai_system_id=row.ai_system_id,
            rule_id=row.rule_id,
            message=row.message,
            created_at=row.created_at,
        )

    def create_violation(
        self, tenant_id: str, ai_system_id: str, rule_id: str, message: str
    ) -> Violation:
        existing = self._session.execute(
            select(ViolationTable).where(
                ViolationTable.tenant_id == tenant_id,
                ViolationTable.ai_system_id == ai_system_id,
                ViolationTable.rule_id == rule_id,
                ViolationTable.message == message,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return self._to_domain(existing)

        row = ViolationTable(
            id=str(uuid4()),
            tenant_id=tenant_id,
            ai_system_id=ai_system_id,
            rule_id=rule_id,
            message=message,
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def list_violations_for_tenant(self, tenant_id: str) -> list[Violation]:
        stmt = (
            select(ViolationTable)
            .where(ViolationTable.tenant_id == tenant_id)
            .order_by(ViolationTable.created_at.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]

    def list_violations_for_ai_system(self, tenant_id: str, ai_system_id: str) -> list[Violation]:
        stmt = (
            select(ViolationTable)
            .where(
                ViolationTable.tenant_id == tenant_id,
                ViolationTable.ai_system_id == ai_system_id,
            )
            .order_by(ViolationTable.created_at.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]
