"""Tests for the enterprise RBAC permission system."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.rbac.dependencies import _resolve_role, require_permission
from app.rbac.permissions import ROLE_PERMISSIONS, Permission, has_permission
from app.rbac.roles import EnterpriseRole

# ── Unit tests: permission matrix ──────────────────────────────────────


def test_viewer_has_view_dashboard_permission() -> None:
    assert has_permission(EnterpriseRole.VIEWER, Permission.VIEW_DASHBOARD)
    assert has_permission(EnterpriseRole.VIEWER, Permission.VIEW_AI_SYSTEMS)
    assert has_permission(EnterpriseRole.VIEWER, Permission.VIEW_COMPLIANCE_STATUS)
    assert has_permission(EnterpriseRole.VIEWER, Permission.VIEW_BOARD_REPORTS)
    assert has_permission(EnterpriseRole.VIEWER, Permission.VIEW_COMPLIANCE_CALENDAR)


def test_viewer_cannot_edit() -> None:
    assert not has_permission(EnterpriseRole.VIEWER, Permission.EDIT_AI_SYSTEMS)
    assert not has_permission(EnterpriseRole.VIEWER, Permission.EDIT_RISK_REGISTER)
    assert not has_permission(EnterpriseRole.VIEWER, Permission.MANAGE_INCIDENTS)
    assert not has_permission(EnterpriseRole.VIEWER, Permission.MANAGE_POLICIES)


def test_compliance_officer_can_manage_incidents() -> None:
    assert has_permission(EnterpriseRole.COMPLIANCE_OFFICER, Permission.MANAGE_INCIDENTS)
    assert has_permission(EnterpriseRole.COMPLIANCE_OFFICER, Permission.MANAGE_POLICIES)
    assert has_permission(EnterpriseRole.COMPLIANCE_OFFICER, Permission.GENERATE_BOARD_REPORTS)
    assert has_permission(EnterpriseRole.COMPLIANCE_OFFICER, Permission.MANAGE_COMPLIANCE_CALENDAR)
    # Also inherits editor/contributor perms
    assert has_permission(EnterpriseRole.COMPLIANCE_OFFICER, Permission.EDIT_AI_SYSTEMS)
    assert has_permission(EnterpriseRole.COMPLIANCE_OFFICER, Permission.VIEW_DASHBOARD)


def test_super_admin_has_all_permissions() -> None:
    for perm in Permission:
        assert has_permission(EnterpriseRole.SUPER_ADMIN, perm), f"SUPER_ADMIN missing {perm}"


def test_role_hierarchy_is_consistent() -> None:
    """Higher roles include all lower role permissions (BOARD_MEMBER excluded)."""
    hierarchy = [
        EnterpriseRole.VIEWER,
        EnterpriseRole.CONTRIBUTOR,
        EnterpriseRole.EDITOR,
        EnterpriseRole.COMPLIANCE_OFFICER,
        EnterpriseRole.CISO,
        EnterpriseRole.TENANT_ADMIN,
        EnterpriseRole.SUPER_ADMIN,
    ]
    for i in range(1, len(hierarchy)):
        lower = hierarchy[i - 1]
        higher = hierarchy[i]
        lower_perms = ROLE_PERMISSIONS[lower]
        higher_perms = ROLE_PERMISSIONS[higher]
        assert lower_perms <= higher_perms, (
            f"{higher} should include all permissions of {lower}; "
            f"missing: {lower_perms - higher_perms}"
        )


def test_board_member_has_restricted_view() -> None:
    perms = ROLE_PERMISSIONS[EnterpriseRole.BOARD_MEMBER]
    assert perms == frozenset(
        {
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_BOARD_REPORTS,
            Permission.VIEW_COMPLIANCE_STATUS,
            Permission.VIEW_COMPLIANCE_CALENDAR,
            Permission.VIEW_EXECUTIVE_DASHBOARD,
            Permission.VIEW_GAP_REPORTS,
            Permission.GENERATE_PDF_REPORT,
        }
    )


def test_auditor_has_export_audit_log() -> None:
    assert has_permission(EnterpriseRole.AUDITOR, Permission.EXPORT_AUDIT_LOG)
    assert has_permission(EnterpriseRole.AUDITOR, Permission.VIEW_AUDIT_LOG)
    assert not has_permission(EnterpriseRole.AUDITOR, Permission.EDIT_AI_SYSTEMS)


# ── Unit tests: role resolution ────────────────────────────────────────


def test_resolve_role_defaults_to_contributor() -> None:
    assert _resolve_role(None) == EnterpriseRole.CONTRIBUTOR
    assert _resolve_role("") == EnterpriseRole.CONTRIBUTOR
    assert _resolve_role("  ") == EnterpriseRole.CONTRIBUTOR


def test_resolve_role_maps_legacy_roles() -> None:
    assert _resolve_role("advisor") == EnterpriseRole.CONTRIBUTOR
    assert _resolve_role("tenant_user") == EnterpriseRole.CONTRIBUTOR
    assert _resolve_role("viewer") == EnterpriseRole.VIEWER
    assert _resolve_role("tenant_admin") == EnterpriseRole.TENANT_ADMIN


def test_resolve_role_maps_new_roles() -> None:
    assert _resolve_role("ciso") == EnterpriseRole.CISO
    assert _resolve_role("super_admin") == EnterpriseRole.SUPER_ADMIN
    assert _resolve_role("board_member") == EnterpriseRole.BOARD_MEMBER
    assert _resolve_role("editor") == EnterpriseRole.EDITOR


# ── Integration tests: FastAPI dependency ──────────────────────────────


def _build_app(permission: Permission) -> FastAPI:
    """Build a minimal FastAPI app with a single guarded endpoint."""
    app = FastAPI()

    @app.get("/protected")
    def protected(
        role: EnterpriseRole = Depends(require_permission(permission)),
    ) -> dict[str, str]:
        return {"role": role}

    return app


def test_require_permission_denies_insufficient_role() -> None:
    app = _build_app(Permission.MANAGE_INCIDENTS)
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/protected", headers={"x-opa-user-role": "viewer"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Insufficient permissions"


def test_require_permission_allows_sufficient_role() -> None:
    app = _build_app(Permission.MANAGE_INCIDENTS)
    client = TestClient(app)
    resp = client.get(
        "/protected",
        headers={"x-opa-user-role": "compliance_officer"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "compliance_officer"


def test_require_permission_default_role_is_contributor() -> None:
    """No header → CONTRIBUTOR; CONTRIBUTOR can view dashboard."""
    app = _build_app(Permission.VIEW_DASHBOARD)
    client = TestClient(app)
    resp = client.get("/protected")
    assert resp.status_code == 200
    assert resp.json()["role"] == "contributor"


def test_require_permission_super_admin_can_do_anything() -> None:
    app = _build_app(Permission.PROVISION_TENANT)
    client = TestClient(app)
    resp = client.get(
        "/protected",
        headers={"x-opa-user-role": "super_admin"},
    )
    assert resp.status_code == 200
