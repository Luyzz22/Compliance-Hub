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
    VIEW_COMPLIANCE_STATUS = "view_compliance_status"
    EDIT_COMPLIANCE_STATUS = "edit_compliance_status"
    MANAGE_POLICIES = "manage_policies"
    VIEW_BOARD_REPORTS = "view_board_reports"
    GENERATE_BOARD_REPORTS = "generate_board_reports"
    MANAGE_TENANT_SETTINGS = "manage_tenant_settings"
    MANAGE_USERS = "manage_users"
    MANAGE_API_KEYS = "manage_api_keys"
    PROVISION_TENANT = "provision_tenant"


_VIEWER_PERMS = frozenset(
    {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_AI_SYSTEMS,
        Permission.VIEW_COMPLIANCE_STATUS,
        Permission.VIEW_BOARD_REPORTS,
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
    }
)

_COMPLIANCE_OFFICER_PERMS = _EDITOR_PERMS | frozenset(
    {
        Permission.MANAGE_INCIDENTS,
        Permission.MANAGE_POLICIES,
        Permission.GENERATE_BOARD_REPORTS,
    }
)

# CISO inherits all compliance_officer perms (VIEW_BOARD_REPORTS and
# GENERATE_BOARD_REPORTS are already present via that chain).
_CISO_PERMS = _COMPLIANCE_OFFICER_PERMS

_BOARD_MEMBER_PERMS = frozenset(
    {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_BOARD_REPORTS,
        Permission.VIEW_COMPLIANCE_STATUS,
    }
)

_TENANT_ADMIN_PERMS = _CISO_PERMS | frozenset(
    {
        Permission.MANAGE_TENANT_SETTINGS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_API_KEYS,
    }
)

_SUPER_ADMIN_PERMS = frozenset(Permission)

ROLE_PERMISSIONS: dict[EnterpriseRole, frozenset[Permission]] = {
    EnterpriseRole.VIEWER: _VIEWER_PERMS,
    EnterpriseRole.CONTRIBUTOR: _CONTRIBUTOR_PERMS,
    EnterpriseRole.EDITOR: _EDITOR_PERMS,
    EnterpriseRole.AUDITOR: _AUDITOR_PERMS,
    EnterpriseRole.COMPLIANCE_OFFICER: _COMPLIANCE_OFFICER_PERMS,
    EnterpriseRole.CISO: _CISO_PERMS,
    EnterpriseRole.BOARD_MEMBER: _BOARD_MEMBER_PERMS,
    EnterpriseRole.TENANT_ADMIN: _TENANT_ADMIN_PERMS,
    EnterpriseRole.SUPER_ADMIN: _SUPER_ADMIN_PERMS,
}


def has_permission(role: EnterpriseRole, permission: Permission) -> bool:
    """Return True if *role* includes *permission*."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
