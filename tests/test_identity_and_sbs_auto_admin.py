"""Tests for identity system, SBS auto-admin, and RBAC role additions.

Covers:
- SBS domain matching (unit)
- Auto-role assignment logic (unit)
- Password policy validation (unit)
- COMPLIANCE_ADMIN role integration
- Registration, verification, login flows (integration via API)
- Password reset flow (integration)
- Profile management (integration)
- Role assignment & tenant isolation (integration)
- Negative tests: unverified SBS, non-SBS, cross-tenant escalation
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.rbac.permissions import Permission, has_permission
from app.rbac.roles import EnterpriseRole
from app.repositories.users import UserRepository
from app.services.identity_service import IdentityService, validate_password_strength
from app.services.sbs_domain_auto_admin import (
    SBS_ADMIN_DOMAINS,
    SBS_BOOTSTRAP_EMAIL,
    is_sbs_domain,
    resolve_auto_role,
)
from tests.conftest import _headers

client = TestClient(app)


# ── Unit Tests: SBS Domain Matching ──────────────────────────────────────────


class TestSbsDomainMatching:
    def test_sbs_de_domain_is_recognised(self) -> None:
        assert is_sbs_domain("user@sbsdeutschland.de") is True

    def test_sbs_com_domain_is_recognised(self) -> None:
        assert is_sbs_domain("user@sbsdeutschland.com") is True

    def test_sbs_domain_case_insensitive(self) -> None:
        assert is_sbs_domain("User@SBSDeutschland.DE") is True
        assert is_sbs_domain("admin@SBSDEUTSCHLAND.COM") is True

    def test_non_sbs_domain_rejected(self) -> None:
        assert is_sbs_domain("user@gmail.com") is False
        assert is_sbs_domain("user@example.de") is False
        assert is_sbs_domain("user@sbs-deutschland.de") is False

    def test_empty_email_rejected(self) -> None:
        assert is_sbs_domain("") is False

    def test_no_at_sign_rejected(self) -> None:
        assert is_sbs_domain("usersbsdeutschland.de") is False

    def test_admin_domains_frozen(self) -> None:
        assert isinstance(SBS_ADMIN_DOMAINS, frozenset)
        assert "sbsdeutschland.de" in SBS_ADMIN_DOMAINS
        assert "sbsdeutschland.com" in SBS_ADMIN_DOMAINS


# ── Unit Tests: Auto-Role Assignment ─────────────────────────────────────────


class TestAutoRoleAssignment:
    def test_bootstrap_email_gets_super_admin(self) -> None:
        role = resolve_auto_role(SBS_BOOTSTRAP_EMAIL, email_verified=True)
        assert role == EnterpriseRole.SUPER_ADMIN

    def test_sbs_verified_gets_tenant_admin(self) -> None:
        role = resolve_auto_role("other@sbsdeutschland.de", email_verified=True)
        assert role == EnterpriseRole.TENANT_ADMIN

    def test_sbs_com_verified_gets_tenant_admin(self) -> None:
        role = resolve_auto_role("other@sbsdeutschland.com", email_verified=True)
        assert role == EnterpriseRole.TENANT_ADMIN

    def test_unverified_sbs_gets_none(self) -> None:
        role = resolve_auto_role("user@sbsdeutschland.de", email_verified=False)
        assert role is None

    def test_non_sbs_verified_gets_none(self) -> None:
        role = resolve_auto_role("user@gmail.com", email_verified=True)
        assert role is None

    def test_non_sbs_unverified_gets_none(self) -> None:
        role = resolve_auto_role("user@example.de", email_verified=False)
        assert role is None

    def test_bootstrap_email_unverified_gets_none(self) -> None:
        """Even the bootstrap email must be verified first."""
        role = resolve_auto_role(SBS_BOOTSTRAP_EMAIL, email_verified=False)
        assert role is None


# ── Unit Tests: Password Policy ──────────────────────────────────────────────


class TestPasswordPolicy:
    def test_short_password_rejected(self) -> None:
        err = validate_password_strength("Short1A")
        assert err is not None
        assert "10" in err

    def test_no_uppercase_rejected(self) -> None:
        err = validate_password_strength("alllowercase1")
        assert err is not None

    def test_no_lowercase_rejected(self) -> None:
        err = validate_password_strength("ALLUPPERCASE1")
        assert err is not None

    def test_no_digit_rejected(self) -> None:
        err = validate_password_strength("NoDigitsHere")
        assert err is not None

    def test_strong_password_accepted(self) -> None:
        err = validate_password_strength("StrongPass1234")
        assert err is None


# ── Unit Tests: COMPLIANCE_ADMIN Role ────────────────────────────────────────


class TestComplianceAdminRole:
    def test_compliance_admin_in_enum(self) -> None:
        assert hasattr(EnterpriseRole, "COMPLIANCE_ADMIN")
        assert EnterpriseRole.COMPLIANCE_ADMIN == "compliance_admin"

    def test_compliance_admin_has_compliance_officer_perms(self) -> None:
        co_perms = {
            Permission.MANAGE_INCIDENTS,
            Permission.MANAGE_POLICIES,
            Permission.GENERATE_BOARD_REPORTS,
            Permission.MANAGE_COMPLIANCE_CALENDAR,
        }
        for perm in co_perms:
            assert has_permission(EnterpriseRole.COMPLIANCE_ADMIN, perm)

    def test_compliance_admin_no_tenant_settings(self) -> None:
        assert not has_permission(
            EnterpriseRole.COMPLIANCE_ADMIN, Permission.MANAGE_TENANT_SETTINGS
        )


# ── Integration Tests: Registration & Verification ──────────────────────────


class TestRegistrationFlow:
    def test_register_new_user(self) -> None:
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "new.user@example.com",
                "password": "StrongPass123",
                "display_name": "New User",
                "company": "Test GmbH",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new.user@example.com"
        assert data["email_verified"] is False
        assert "verification_token" in data
        assert "user_id" in data

    def test_register_duplicate_email(self) -> None:
        first = client.post(
            "/api/v1/auth/register",
            json={"email": "dup@example.com", "password": "StrongPass123"},
        )
        assert first.status_code == 201
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "dup@example.com", "password": "StrongPass123"},
        )
        assert resp.status_code == 409

    def test_register_weak_password(self) -> None:
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "weak@example.com", "password": "short"},
        )
        assert resp.status_code == 400

    def test_verify_email_with_valid_token(self) -> None:
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": "verify.me@example.com", "password": "StrongPass123"},
        )
        token = reg.json()["verification_token"]
        resp = client.post(f"/api/v1/auth/verify-email?token={token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["email_verified"] is True

    def test_verify_email_invalid_token(self) -> None:
        resp = client.post("/api/v1/auth/verify-email?token=invalid-token-xyz")
        assert resp.status_code == 400

    def test_sbs_user_gets_auto_role_after_verification(self) -> None:
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": "auto.admin@sbsdeutschland.de",
                "password": "StrongPass123",
            },
        )
        token = reg.json()["verification_token"]
        resp = client.post(f"/api/v1/auth/verify-email?token={token}")
        data = resp.json()
        assert data["auto_role"] == "tenant_admin"

    def test_bootstrap_email_gets_super_admin_after_verification(self) -> None:
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": "ki@sbsdeutschland.de", "password": "StrongPass123"},
        )
        token = reg.json()["verification_token"]
        resp = client.post(f"/api/v1/auth/verify-email?token={token}")
        data = resp.json()
        assert data["auto_role"] == "super_admin"


# ── Integration Tests: Login ─────────────────────────────────────────────────


class TestLoginFlow:
    def test_login_success(self) -> None:
        client.post(
            "/api/v1/auth/register",
            json={"email": "login.ok@example.com", "password": "StrongPass123"},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "login.ok@example.com", "password": "StrongPass123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "login.ok@example.com"

    def test_login_wrong_password(self) -> None:
        client.post(
            "/api/v1/auth/register",
            json={"email": "login.wrong@example.com", "password": "StrongPass123"},
        )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "login.wrong@example.com", "password": "WrongPass999"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_email(self) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "no.such.user@example.com", "password": "StrongPass123"},
        )
        assert resp.status_code == 401

    def test_login_lockout_after_max_failures(self) -> None:
        client.post(
            "/api/v1/auth/register",
            json={"email": "lockout@example.com", "password": "StrongPass123"},
        )
        for _ in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"email": "lockout@example.com", "password": "WrongWrong1"},
            )
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "lockout@example.com", "password": "StrongPass123"},
        )
        assert resp.status_code == 429


# ── Integration Tests: Password Reset ────────────────────────────────────────


class TestPasswordReset:
    def test_request_reset_existing_email(self) -> None:
        client.post(
            "/api/v1/auth/register",
            json={"email": "reset.me@example.com", "password": "StrongPass123"},
        )
        resp = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "reset.me@example.com"},
        )
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_request_reset_nonexistent_email_no_leak(self) -> None:
        resp = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "nonexistent@example.com"},
        )
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_confirm_reset_with_valid_token(self) -> None:
        client.post(
            "/api/v1/auth/register",
            json={"email": "reset.confirm@example.com", "password": "StrongPass123"},
        )
        # Get token via service directly (simulating email delivery)
        with Session(engine) as s:
            repo = UserRepository(s)
            svc = IdentityService(repo)
            result = svc.request_password_reset("reset.confirm@example.com")
            token = result.get("reset_token")
        assert token is not None

        resp = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": token, "new_password": "NewStrongPass1"},
        )
        assert resp.status_code == 200
        # Login with new password
        resp2 = client.post(
            "/api/v1/auth/login",
            json={"email": "reset.confirm@example.com", "password": "NewStrongPass1"},
        )
        assert resp2.status_code == 200

    def test_confirm_reset_invalid_token(self) -> None:
        resp = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": "bad-token", "new_password": "NewStrongPass1"},
        )
        assert resp.status_code == 400


# ── Integration Tests: Profile ───────────────────────────────────────────────


class TestProfile:
    def test_get_profile(self) -> None:
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": "profile.get@example.com",
                "password": "StrongPass123",
                "display_name": "Profile User",
            },
        )
        user_id = reg.json()["user_id"]
        headers = _headers()
        resp = client.get(f"/api/v1/auth/profile/{user_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "profile.get@example.com"
        assert data["display_name"] == "Profile User"

    def test_get_profile_not_found(self) -> None:
        headers = _headers()
        resp = client.get("/api/v1/auth/profile/nonexistent-id", headers=headers)
        assert resp.status_code == 404

    def test_update_profile(self) -> None:
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": "profile.update@example.com", "password": "StrongPass123"},
        )
        user_id = reg.json()["user_id"]
        headers = _headers()
        resp = client.put(
            f"/api/v1/auth/profile/{user_id}",
            headers=headers,
            json={"display_name": "Updated Name", "company": "Updated GmbH"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Updated Name"
        assert data["company"] == "Updated GmbH"


# ── Integration Tests: Role Assignment & Tenant Isolation ────────────────────


class TestRoleAssignment:
    def test_assign_role_to_user(self) -> None:
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": "role.assign@example.com", "password": "StrongPass123"},
        )
        user_id = reg.json()["user_id"]
        headers = {**_headers(), "x-opa-user-role": "tenant_admin"}
        resp = client.post(
            "/api/v1/auth/roles/assign",
            headers=headers,
            json={
                "user_id": user_id,
                "tenant_id": "test-tenant-1",
                "role": "editor",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "editor"
        assert data["tenant_id"] == "test-tenant-1"

    def test_assign_role_requires_manage_users_permission(self) -> None:
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": "role.noperm@example.com", "password": "StrongPass123"},
        )
        user_id = reg.json()["user_id"]
        headers = {**_headers(), "x-opa-user-role": "viewer"}
        resp = client.post(
            "/api/v1/auth/roles/assign",
            headers=headers,
            json={
                "user_id": user_id,
                "tenant_id": "test-tenant-1",
                "role": "editor",
            },
        )
        assert resp.status_code == 403

    def test_list_tenant_users(self) -> None:
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": "list.user@example.com", "password": "StrongPass123"},
        )
        user_id = reg.json()["user_id"]
        admin_headers = {**_headers(), "x-opa-user-role": "tenant_admin"}
        client.post(
            "/api/v1/auth/roles/assign",
            headers=admin_headers,
            json={
                "user_id": user_id,
                "tenant_id": _headers()["x-tenant-id"],
                "role": "editor",
            },
        )
        resp = client.get("/api/v1/auth/users", headers=admin_headers)
        assert resp.status_code == 200
        users = resp.json()
        assert any(u["user_id"] == user_id for u in users)


# ── Negative Tests ───────────────────────────────────────────────────────────


class TestNegativeCases:
    def test_unverified_sbs_mail_gets_no_admin(self) -> None:
        """SBS domain user who hasn't verified email must NOT get auto-admin."""
        role = resolve_auto_role("unverified@sbsdeutschland.de", email_verified=False)
        assert role is None

    def test_non_sbs_mail_gets_no_auto_admin(self) -> None:
        """Non-SBS domain user must NOT get auto-admin even if verified."""
        role = resolve_auto_role("verified@gmail.com", email_verified=True)
        assert role is None

    def test_sbs_like_domain_no_auto_admin(self) -> None:
        """Similar but non-matching domain must NOT get auto-admin."""
        assert resolve_auto_role("user@sbs-deutschland.de", email_verified=True) is None
        assert resolve_auto_role("user@sbsdeutschland.org", email_verified=True) is None

    def test_cross_tenant_role_escalation_blocked(self) -> None:
        """Viewer cannot assign roles (RBAC enforcement)."""
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": "cross.tenant@example.com", "password": "StrongPass123"},
        )
        user_id = reg.json()["user_id"]
        viewer_headers = {**_headers(), "x-opa-user-role": "viewer"}
        resp = client.post(
            "/api/v1/auth/roles/assign",
            headers=viewer_headers,
            json={
                "user_id": user_id,
                "tenant_id": "other-tenant-99",
                "role": "super_admin",
            },
        )
        assert resp.status_code == 403

    def test_register_sbs_user_no_auto_role_without_verification(self) -> None:
        """Registration alone does NOT grant auto-admin to SBS domain user."""
        reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": "norole.yet@sbsdeutschland.de",
                "password": "StrongPass123",
            },
        )
        assert reg.status_code == 201
        data = reg.json()
        assert data["email_verified"] is False
        # No auto_role field in registration response
        assert "auto_role" not in data
