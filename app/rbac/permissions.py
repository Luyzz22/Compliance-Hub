"""Permission enum and role-permission mapping for enterprise RBAC."""

from __future__ import annotations

from enum import StrEnum

from app.rbac.roles import EnterpriseRole


class Permission(StrEnum):
    VIEW_DASHBOARD = "view_dashboard"
    VIEW_AI_SYSTEMS = "view_ai_systems"
    EDIT_AI_SYSTEMS = "edit_ai_systems"
    VIEW_RISK_REGISTER = "view_risk_register"
    EDIT_RISK_REGISTER = "edit_risk_register"
    VIEW_INCIDENTS = "view_incidents"
    MANAGE_INCIDENTS = "manage_incidents"
    VIEW_AUDIT_LOG = "view_audit_log"
    EXPORT_AUDIT_LOG = "export_audit_log"
    VIEW_COMPLIANCE_CALENDAR = "view_compliance_calendar"
    MANAGE_COMPLIANCE_CALENDAR = "manage_compliance_calendar"
    VIEW_COMPLIANCE_STATUS = "view_compliance_status"
    EDIT_COMPLIANCE_STATUS = "edit_compliance_status"
    MANAGE_POLICIES = "manage_policies"
    VIEW_BOARD_REPORTS = "view_board_reports"
    GENERATE_BOARD_REPORTS = "generate_board_reports"
    MANAGE_TENANT_SETTINGS = "manage_tenant_settings"
    MANAGE_USERS = "manage_users"
    MANAGE_API_KEYS = "manage_api_keys"
    MANAGE_ONBOARDING_READINESS = "manage_onboarding_readiness"
    PROVISION_TENANT = "provision_tenant"
    MANAGE_IDENTITY_PROVIDERS = "manage_identity_providers"
    MANAGE_SCIM = "manage_scim"
    MANAGE_ACCESS_REVIEWS = "manage_access_reviews"
    MANAGE_SOD_POLICIES = "manage_sod_policies"
    MANAGE_APPROVAL_WORKFLOWS = "manage_approval_workflows"
    MANAGE_MFA = "manage_mfa"
    VIEW_PRIVILEGED_EVENTS = "view_privileged_events"
    EXPORT_DATEV = "export_datev"
    VIEW_GAP_REPORTS = "view_gap_reports"
    RUN_GAP_ANALYSIS = "run_gap_analysis"
    VIEW_EXECUTIVE_DASHBOARD = "view_executive_dashboard"


_VIEWER_PERMS = frozenset(
    {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_AI_SYSTEMS,
        Permission.VIEW_COMPLIANCE_STATUS,
        Permission.VIEW_BOARD_REPORTS,
        Permission.VIEW_COMPLIANCE_CALENDAR,
    }
)

_CONTRIBUTOR_PERMS = _VIEWER_PERMS | frozenset(
    {
        Permission.VIEW_RISK_REGISTER,
        Permission.VIEW_INCIDENTS,
        Permission.VIEW_AUDIT_LOG,
    }
)

_EDITOR_PERMS = _CONTRIBUTOR_PERMS | frozenset(
    {
        Permission.EDIT_AI_SYSTEMS,
        Permission.EDIT_RISK_REGISTER,
        Permission.EDIT_COMPLIANCE_STATUS,
    }
)

_AUDITOR_PERMS = _CONTRIBUTOR_PERMS | frozenset(
    {
        Permission.EXPORT_AUDIT_LOG,
        Permission.VIEW_COMPLIANCE_CALENDAR,
        Permission.VIEW_PRIVILEGED_EVENTS,
    }
)

_COMPLIANCE_OFFICER_PERMS = _EDITOR_PERMS | frozenset(
    {
        Permission.MANAGE_INCIDENTS,
        Permission.MANAGE_POLICIES,
        Permission.GENERATE_BOARD_REPORTS,
        Permission.MANAGE_COMPLIANCE_CALENDAR,
        Permission.MANAGE_ONBOARDING_READINESS,
    }
)

# CISO inherits all compliance_officer perms (VIEW_BOARD_REPORTS and
# GENERATE_BOARD_REPORTS are already present via that chain).
_CISO_PERMS = _COMPLIANCE_OFFICER_PERMS | frozenset(
    {
        Permission.VIEW_EXECUTIVE_DASHBOARD,
        Permission.VIEW_GAP_REPORTS,
        Permission.RUN_GAP_ANALYSIS,
    }
)

_BOARD_MEMBER_PERMS = frozenset(
    {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_BOARD_REPORTS,
        Permission.VIEW_COMPLIANCE_STATUS,
        Permission.VIEW_COMPLIANCE_CALENDAR,
        Permission.VIEW_EXECUTIVE_DASHBOARD,
        Permission.VIEW_GAP_REPORTS,
    }
)

_COMPLIANCE_ADMIN_PERMS = _COMPLIANCE_OFFICER_PERMS | frozenset(
    {
        Permission.VIEW_EXECUTIVE_DASHBOARD,
        Permission.VIEW_GAP_REPORTS,
        Permission.RUN_GAP_ANALYSIS,
        Permission.EXPORT_DATEV,
    }
)

_TENANT_ADMIN_PERMS = _CISO_PERMS | frozenset(
    {
        Permission.MANAGE_TENANT_SETTINGS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_API_KEYS,
        Permission.MANAGE_ONBOARDING_READINESS,
        Permission.MANAGE_IDENTITY_PROVIDERS,
        Permission.MANAGE_SCIM,
        Permission.MANAGE_ACCESS_REVIEWS,
        Permission.MANAGE_SOD_POLICIES,
        Permission.MANAGE_APPROVAL_WORKFLOWS,
        Permission.MANAGE_MFA,
        Permission.VIEW_PRIVILEGED_EVENTS,
        Permission.EXPORT_DATEV,
    }
)

_SUPER_ADMIN_PERMS = frozenset(Permission)

ROLE_PERMISSIONS: dict[EnterpriseRole, frozenset[Permission]] = {
    EnterpriseRole.VIEWER: _VIEWER_PERMS,
    EnterpriseRole.CONTRIBUTOR: _CONTRIBUTOR_PERMS,
    EnterpriseRole.EDITOR: _EDITOR_PERMS,
    EnterpriseRole.AUDITOR: _AUDITOR_PERMS,
    EnterpriseRole.COMPLIANCE_OFFICER: _COMPLIANCE_OFFICER_PERMS,
    EnterpriseRole.COMPLIANCE_ADMIN: _COMPLIANCE_ADMIN_PERMS,
    EnterpriseRole.CISO: _CISO_PERMS,
    EnterpriseRole.BOARD_MEMBER: _BOARD_MEMBER_PERMS,
    EnterpriseRole.TENANT_ADMIN: _TENANT_ADMIN_PERMS,
    EnterpriseRole.SUPER_ADMIN: _SUPER_ADMIN_PERMS,
}


def has_permission(role: EnterpriseRole, permission: Permission) -> bool:
    """Return True if *role* includes *permission*."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
