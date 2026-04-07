from __future__ import annotations

from enum import StrEnum


class GovernanceAuditEntity(StrEnum):
    """Canonical audit entity types for enterprise governance flows."""

    NIS2_INCIDENT = "nis2_incident"
    COMPLIANCE_DEADLINE = "compliance_deadline"
    COMPLIANCE_CALENDAR = "compliance_calendar"
    AUTHORITY_EXPORT = "authority_export"
    AUTHORITY_AUDIT_PREPARATION_PACK = "authority_audit_preparation_pack"
    ENTERPRISE_ONBOARDING_READINESS = "enterprise_onboarding_readiness"


class GovernanceAuditAction(StrEnum):
    """Canonical audit actions for security-relevant governance events."""

    NIS2_INCIDENT_CREATE = "nis2.incident.create"
    NIS2_INCIDENT_TRANSITION = "nis2.incident.transition"
    NIS2_INCIDENT_DEADLINE_OVERRIDE = "nis2.incident.deadlines.override"
    COMPLIANCE_DEADLINE_CREATE = "compliance_calendar.deadline.create"
    COMPLIANCE_DEADLINE_UPDATE = "compliance_calendar.deadline.update"
    COMPLIANCE_DEADLINE_DELETE = "compliance_calendar.deadline.delete"
    COMPLIANCE_CALENDAR_SEED_DEFAULTS = "compliance_calendar.seed_defaults"
    AUTHORITY_EXPORT_GENERATED = "generated"
    AUTHORITY_EXPORT_API_ACTION = "export_authority_ai_act"
    AUTHORITY_AUDIT_PACK_GENERATED = "authority_audit_pack.generated"
    ENTERPRISE_ONBOARDING_READINESS_UPSERT = "enterprise_onboarding_readiness.upsert"


class NIS2DeadlinePolicy:
    """Deterministic default offsets; legal interpretation remains advisor-led."""

    NOTIFICATION_HOURS = 24
    REPORT_HOURS = 72
    FINAL_REPORT_DAYS_AFTER_REPORT = 30
