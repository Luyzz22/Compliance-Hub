"""Enterprise RBAC role definitions for ComplianceHub."""

from __future__ import annotations

from enum import StrEnum


class EnterpriseRole(StrEnum):
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    EDITOR = "editor"
    AUDITOR = "auditor"
    COMPLIANCE_OFFICER = "compliance_officer"
    CISO = "ciso"
    BOARD_MEMBER = "board_member"
    COMPLIANCE_ADMIN = "compliance_admin"
    TENANT_ADMIN = "tenant_admin"
    SUPER_ADMIN = "super_admin"
