from __future__ import annotations

from collections import Counter
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.policy_models import Severity
from app.repositories.ai_systems import AISystemRepository
from app.repositories.audit import AuditEventTable
from app.repositories.policies import PolicyRepository
from app.repositories.violations import ViolationRepository


class TenantComplianceOverview(BaseModel):
    tenant_id: str
    total_systems: int
    compliant_systems: int
    partially_compliant_systems: int
    non_compliant_systems: int
    violations_by_rule: dict[str, int]
    violations_by_severity: dict[str, int]
    last_evaluated_at: datetime | None = None


def compute_tenant_compliance_overview(
    tenant_id: str,
    session: Session,
) -> TenantComplianceOverview:
    ai_repo = AISystemRepository(session)
    policy_repo = PolicyRepository(session)
    violation_repo = ViolationRepository(session)

    systems = ai_repo.list_for_tenant(tenant_id)
    violations = violation_repo.list_violations_for_tenant(tenant_id)

    rule_severity_map: dict[str, Severity] = {}
    for policy in policy_repo.list_policies_for_tenant(tenant_id):
        for rule in policy.rules:
            rule_severity_map[rule.id] = rule.severity

    violations_by_rule = dict(Counter(v.rule_id for v in violations))

    violations_by_severity_counter: Counter[str] = Counter()
    violations_by_system_severity: dict[str, set[Severity]] = {}

    for violation in violations:
        severity = rule_severity_map.get(violation.rule_id)
        if severity is None:
            continue

        violations_by_severity_counter[severity.value] += 1
        system_severities = violations_by_system_severity.setdefault(violation.ai_system_id, set())
        system_severities.add(severity)

    compliant_systems = 0
    partially_compliant_systems = 0
    non_compliant_systems = 0

    for system in systems:
        severities = violations_by_system_severity.get(system.id, set())
        if not severities:
            compliant_systems += 1
            continue

        if Severity.high in severities or Severity.critical in severities:
            non_compliant_systems += 1
        else:
            partially_compliant_systems += 1

    last_eval_stmt = (
        select(AuditEventTable.timestamp)
        .where(
            AuditEventTable.tenant_id == tenant_id,
            AuditEventTable.action == "policy_evaluated",
            AuditEventTable.entity_type == "ai_system",
        )
        .order_by(AuditEventTable.timestamp.desc())
        .limit(1)
    )
    last_evaluated_at = session.execute(last_eval_stmt).scalar_one_or_none()

    return TenantComplianceOverview(
        tenant_id=tenant_id,
        total_systems=len(systems),
        compliant_systems=compliant_systems,
        partially_compliant_systems=partially_compliant_systems,
        non_compliant_systems=non_compliant_systems,
        violations_by_rule=violations_by_rule,
        violations_by_severity=dict(violations_by_severity_counter),
        last_evaluated_at=last_evaluated_at,
    )
