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
    ENTERPRISE_INTEGRATION_BLUEPRINT = "enterprise_integration_blueprint"
    ENTERPRISE_CONNECTOR_RUNTIME = "enterprise_connector_runtime"
    AI_GOVERNANCE_ACTION = "ai_governance_action"
    TENANT_API_KEY = "tenant_api_key"
    EVIDENCE_FILE = "evidence_file"
    SERVICE_HEALTH_SNAPSHOT = "service_health_snapshot"
    SERVICE_HEALTH_INCIDENT = "service_health_incident"
    GOVERNANCE_CONTROL = "governance_control"
    GOVERNANCE_CONTROL_EVIDENCE = "governance_control_evidence"
    GOVERNANCE_AUDIT_CASE = "governance_audit_case"


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
    ENTERPRISE_INTEGRATION_BLUEPRINT_UPSERT = "enterprise_integration_blueprint.upsert"
    ENTERPRISE_CONNECTOR_SYNC_TRIGGERED = "enterprise_connector.sync.triggered"
    ENTERPRISE_CONNECTOR_SYNC_COMPLETED = "enterprise_connector.sync.completed"
    ENTERPRISE_CONNECTOR_SYNC_RETRY_TRIGGERED = "enterprise_connector.sync.retry_triggered"
    AI_GOVERNANCE_ACTION_CREATE = "ai_governance_action.create"
    AI_GOVERNANCE_ACTION_UPDATE = "ai_governance_action.update"
    AI_GOVERNANCE_ACTION_DELETE = "ai_governance_action.delete"
    TENANT_API_KEY_CREATE = "tenant_api_key.create"
    TENANT_API_KEY_REVOKE = "tenant_api_key.revoke"
    EVIDENCE_DELETE = "evidence.delete"
    SERVICE_HEALTH_POLL_COMPLETED = "service_health.poll.completed"
    SERVICE_HEALTH_INCIDENT_DETECTED = "service_health.incident.detected"
    SERVICE_HEALTH_INCIDENT_RESOLVED = "service_health.incident.resolved"
    GOVERNANCE_CONTROL_CREATE = "governance_control.create"
    GOVERNANCE_CONTROL_UPDATE = "governance_control.update"
    GOVERNANCE_CONTROL_EVIDENCE_ADD = "governance_control.evidence.add"
    GOVERNANCE_AUDIT_CASE_CREATE = "governance_audit_case.create"
    GOVERNANCE_AUDIT_CASE_CONTROL_ATTACH = "governance_audit_case.control.attach"


class NIS2DeadlinePolicy:
    """Deterministic default offsets; legal interpretation remains advisor-led."""

    NOTIFICATION_HOURS = 24
    REPORT_HOURS = 72
    FINAL_REPORT_DAYS_AFTER_REPORT = 30
