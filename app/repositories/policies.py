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


        if condition_type == RuleConditionType.incident_response_runbook_required:
            return Rule(
                id=row.id,
                policy_id=row.policy_id,
                tenant_id=row.tenant_id,
                name=row.name,
                description=(
                    row.description or "NIS2/ISO27001: Incident response runbook is required"
                ),
                severity=Severity.high,
                message="Missing incident response runbook for AI system.",
                conditions=[
                    PolicyRuleCondition(field_path="has_incident_runbook", expected=False),
                ],
            )

        if condition_type == RuleConditionType.supplier_risk_assessment_required:
            return Rule(
                id=row.id,
                policy_id=row.policy_id,
                tenant_id=row.tenant_id,
                name=row.name,
                description=(
                    row.description
                    or "NIS2/ISO27001: Supplier risk assessment register is required"
                ),
                severity=Severity.high,
                message="Missing supplier risk assessment register for AI system.",
                conditions=[
                    PolicyRuleCondition(
                        field_path="has_supplier_risk_register",
                        expected=False,
                    ),
                ],
            )

        if condition_type == RuleConditionType.backup_and_recovery_plan_required:
            return Rule(
                id=row.id,
                policy_id=row.policy_id,
                tenant_id=row.tenant_id,
                name=row.name,
                description=(
                    row.description
                    or "NIS2/ISO27001: Backup and recovery runbook is required"
                ),
                severity=Severity.high,
                message="Missing backup and recovery runbook for AI system.",
                conditions=[
                    PolicyRuleCondition(field_path="has_backup_runbook", expected=False),
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

            Policy(
                id="builtin-nis2-incident-runbook",
                tenant_id=tenant_id,
                name="Builtin: Incident response runbook required",
                description=(
                    "NIS2 Art. 21(2) Nr. 2 / ISO 27001 A.5.29 - "
                    "AI systems must have a documented incident response runbook."
                ),
                rules=[
                    Rule(
                        id="nis2-incident-runbook-missing",
                        policy_id="builtin-nis2-incident-runbook",
                        tenant_id=tenant_id,
                        name="Incident response runbook required",
                        description=(
                            "Map: NIS2 Art. 21(2) Nr. 2; ISO 27001 A.5.29. "
                            "Violation if has_incident_runbook is false."
                        ),
                        severity=Severity.high,
                        message="Missing incident response runbook for AI system.",
                        conditions=[
                            PolicyRuleCondition(
                                field_path="has_incident_runbook",
                                expected=False,
                            ),
                        ],
                    )
                ],
            ),
            Policy(
                id="builtin-nis2-supplier-risk",
                tenant_id=tenant_id,
                name="Builtin: Supplier risk assessment required",
                description=(
                    "NIS2 Art. 21(2) Nr. 4 / ISO 27001 A.5.21 - "
                    "AI systems must be covered by supplier risk assessments."
                ),
                rules=[
                    Rule(
                        id="nis2-supplier-risk-register-missing",
                        policy_id="builtin-nis2-supplier-risk",
                        tenant_id=tenant_id,
                        name="Supplier risk assessment register required",
                        description=(
                            "Map: NIS2 Art. 21(2) Nr. 4; ISO 27001 A.5.21. "
                            "Violation if has_supplier_risk_register is false."
                        ),
                        severity=Severity.high,
                        message="Missing supplier risk assessment register for AI system.",
                        conditions=[
                            PolicyRuleCondition(
                                field_path="has_supplier_risk_register",
                                expected=False,
                            ),
                        ],
                    )
                ],
            ),
            Policy(
                id="builtin-nis2-backup-recovery",
                tenant_id=tenant_id,
                name="Builtin: Backup and recovery plan required",
                description=(
                    "NIS2 Art. 21(2) Nr. 3 / ISO 27001 A.5.30 - "
                    "AI systems must have backup and recovery plans."
                ),
                rules=[
                    Rule(
                        id="nis2-backup-recovery-missing",
                        policy_id="builtin-nis2-backup-recovery",
                        tenant_id=tenant_id,
                        name="Backup and recovery plan required",
                        description=(
                            "Map: NIS2 Art. 21(2) Nr. 3; ISO 27001 A.5.30. "
                            "Violation if has_backup_runbook is false."
                        ),
                        severity=Severity.high,
                        message="Missing backup and recovery runbook for AI system.",
                        conditions=[
                            PolicyRuleCondition(
                                field_path="has_backup_runbook",
                                expected=False,
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

    def ensure_default_policies(self, tenant_id: str) -> None:
        self.ensure_default_policy_rules(tenant_id)

    def ensure_default_policy_rules(self, tenant_id: str) -> None:
        default_policies = [
            (
                f"{tenant_id}-default-policy",
                "Default AI Compliance Policy",
                "Default baseline compliance checks for EU AI Act.",
            ),
            (
                f"{tenant_id}-nis2-iso27001-incident-response",
                "NIS2/ISO27001 Incident Response",
                (
                    "Mapping: NIS2 Art. 21(2) Nr. 2 / ISO 27001 A.5.29 - "
                    "incident response runbook required."
                ),
            ),
            (
                f"{tenant_id}-nis2-iso27001-supplier-risk",
                "NIS2/ISO27001 Supplier Risk",
                (
                    "Mapping: NIS2 Art. 21(2) Nr. 4 / ISO 27001 A.5.21 - "
                    "supplier risk assessment register required."
                ),
            ),
            (
                f"{tenant_id}-nis2-iso27001-backup-recovery",
                "NIS2/ISO27001 Backup & Recovery",
                (
                    "Mapping: NIS2 Art. 21(2) Nr. 3 / ISO 27001 A.5.30 - "
                    "backup and recovery runbook required."
                ),
            ),
        ]

        for policy_id, name, description in default_policies:
            if self._session.get(PolicyTable, policy_id) is None:
                self._session.add(
                    PolicyTable(
                        id=policy_id,
                        tenant_id=tenant_id,
                        name=name,
                        description=description,
                        active=True,
                    )
                )

