from __future__ import annotations

from app.governance_taxonomy import (
    GovernanceAuditAction,
    GovernanceAuditEntity,
    NIS2DeadlinePolicy,
)


def test_governance_audit_taxonomy_values_are_stable() -> None:
    assert GovernanceAuditEntity.NIS2_INCIDENT.value == "nis2_incident"
    assert GovernanceAuditEntity.COMPLIANCE_DEADLINE.value == "compliance_deadline"
    assert GovernanceAuditEntity.AUTHORITY_EXPORT.value == "authority_export"
    assert GovernanceAuditAction.NIS2_INCIDENT_CREATE.value == "nis2.incident.create"
    assert (
        GovernanceAuditAction.NIS2_INCIDENT_DEADLINE_OVERRIDE.value
        == "nis2.incident.deadlines.override"
    )
    assert GovernanceAuditAction.COMPLIANCE_CALENDAR_SEED_DEFAULTS.value == (
        "compliance_calendar.seed_defaults"
    )


def test_nis2_deadline_policy_defaults() -> None:
    assert NIS2DeadlinePolicy.NOTIFICATION_HOURS == 24
    assert NIS2DeadlinePolicy.REPORT_HOURS == 72
    assert NIS2DeadlinePolicy.FINAL_REPORT_DAYS_AFTER_REPORT == 30
