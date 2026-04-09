"""Tests for enterprise governance: SoD, MFA, Approval Workflows, Privileged Access.

Covers:
- SoD policy CRUD and conflict detection (unit + integration)
- MFA TOTP enrollment / verification / reset
- MFA backup codes generation and verification
- Step-up MFA challenge
- Approval workflow creation, decision, self-approval prevention
- Approval expiry
- Privileged action event logging
- Negative tests: bypass prevention, self-approval blocked, SoD conflict blocks role assignment
- Integration: privileged role assignment with SoD check
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models_db import UserDB, UserTenantRoleDB
from app.rbac.permissions import Permission, has_permission
from app.rbac.roles import EnterpriseRole
from app.services.enterprise_governance_service import (
    STEP_UP_ACTIONS,
    ApprovalWorkflowService,
    MFAService,
    PrivilegedActionService,
    SoDService,
    _current_totp,
    _generate_totp_secret,
    _verify_totp,
    is_privileged_role,
)
from tests.conftest import _headers

client = TestClient(app)

_TENANT = "board-kpi-tenant"


def _admin_headers() -> dict[str, str]:
    return {**_headers(), "x-opa-user-role": "tenant_admin"}


def _super_admin_headers() -> dict[str, str]:
    return {**_headers(), "x-opa-user-role": "super_admin"}


def _ensure_test_user(session: Session, email: str = "gov-test@example.com") -> str:
    """Create a test user if not present, return user_id."""
    existing = session.execute(
        __import__("sqlalchemy").select(UserDB).where(UserDB.email == email)
    ).scalar_one_or_none()
    if existing:
        return existing.id
    from datetime import UTC, datetime

    uid = str(uuid.uuid4())
    user = UserDB(
        id=uid,
        email=email,
        password_hash="!test_no_login",
        display_name="Gov Test User",
        email_verified=True,
        is_active=True,
        created_at_utc=datetime.now(UTC),
        updated_at_utc=datetime.now(UTC),
    )
    session.add(user)
    session.commit()
    return uid


# ── Unit Tests: New RBAC Permissions ─────────────────────────────────────────


class TestGovernancePermissions:
    def test_manage_sod_in_enum(self) -> None:
        assert hasattr(Permission, "MANAGE_SOD_POLICIES")

    def test_manage_approval_workflows_in_enum(self) -> None:
        assert hasattr(Permission, "MANAGE_APPROVAL_WORKFLOWS")

    def test_manage_mfa_in_enum(self) -> None:
        assert hasattr(Permission, "MANAGE_MFA")

    def test_view_privileged_events_in_enum(self) -> None:
        assert hasattr(Permission, "VIEW_PRIVILEGED_EVENTS")

    def test_tenant_admin_has_sod_permission(self) -> None:
        assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.MANAGE_SOD_POLICIES)

    def test_tenant_admin_has_approval_permission(self) -> None:
        assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.MANAGE_APPROVAL_WORKFLOWS)

    def test_tenant_admin_has_mfa_permission(self) -> None:
        assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.MANAGE_MFA)

    def test_super_admin_has_all_governance_permissions(self) -> None:
        assert has_permission(EnterpriseRole.SUPER_ADMIN, Permission.MANAGE_SOD_POLICIES)
        assert has_permission(EnterpriseRole.SUPER_ADMIN, Permission.MANAGE_APPROVAL_WORKFLOWS)
        assert has_permission(EnterpriseRole.SUPER_ADMIN, Permission.MANAGE_MFA)
        assert has_permission(EnterpriseRole.SUPER_ADMIN, Permission.VIEW_PRIVILEGED_EVENTS)

    def test_auditor_can_view_privileged_events(self) -> None:
        assert has_permission(EnterpriseRole.AUDITOR, Permission.VIEW_PRIVILEGED_EVENTS)

    def test_viewer_cannot_manage_sod(self) -> None:
        assert not has_permission(EnterpriseRole.VIEWER, Permission.MANAGE_SOD_POLICIES)

    def test_viewer_cannot_manage_approvals(self) -> None:
        assert not has_permission(EnterpriseRole.VIEWER, Permission.MANAGE_APPROVAL_WORKFLOWS)

    def test_viewer_cannot_manage_mfa(self) -> None:
        assert not has_permission(EnterpriseRole.VIEWER, Permission.MANAGE_MFA)

    def test_viewer_cannot_view_privileged_events(self) -> None:
        assert not has_permission(EnterpriseRole.VIEWER, Permission.VIEW_PRIVILEGED_EVENTS)


# ── Unit Tests: is_privileged_role ───────────────────────────────────────────


class TestPrivilegedRoleDetection:
    def test_super_admin_is_privileged(self) -> None:
        assert is_privileged_role("super_admin")

    def test_tenant_admin_is_privileged(self) -> None:
        assert is_privileged_role("tenant_admin")

    def test_compliance_admin_is_privileged(self) -> None:
        assert is_privileged_role("compliance_admin")

    def test_auditor_is_privileged(self) -> None:
        assert is_privileged_role("auditor")

    def test_viewer_is_not_privileged(self) -> None:
        assert not is_privileged_role("viewer")

    def test_editor_is_not_privileged(self) -> None:
        assert not is_privileged_role("editor")


# ── Unit Tests: TOTP Low-Level ───────────────────────────────────────────────


class TestTOTPImplementation:
    def test_generate_secret_length(self) -> None:
        secret = _generate_totp_secret()
        assert len(secret) == 40  # 20 bytes -> 40 hex chars

    def test_current_totp_returns_6_digits(self) -> None:
        secret = _generate_totp_secret()
        code = _current_totp(secret)
        assert len(code) == 6
        assert code.isdigit()

    def test_verify_totp_current(self) -> None:
        secret = _generate_totp_secret()
        code = _current_totp(secret)
        assert _verify_totp(secret, code)

    def test_verify_totp_wrong_code(self) -> None:
        secret = _generate_totp_secret()
        assert not _verify_totp(secret, "000000")

    def test_verify_totp_wrong_secret(self) -> None:
        secret1 = _generate_totp_secret()
        secret2 = _generate_totp_secret()
        code = _current_totp(secret1)
        assert not _verify_totp(secret2, code)


# ── Unit Tests: SoD Policy Evaluation ────────────────────────────────────────


class TestSoDServiceUnit:
    def test_create_and_list_policy(self) -> None:
        with Session(engine) as s:
            svc = SoDService(s)
            result = svc.create_policy(
                _TENANT,
                "super_admin",
                "auditor",
                description="Admin and auditor cannot coexist",
                severity="block",
            )
            assert "error" not in result
            assert result["role_a"] in ("auditor", "super_admin")
            assert result["role_b"] in ("auditor", "super_admin")
            policies = svc.list_policies(_TENANT)
            assert any(p["id"] == result["id"] for p in policies)
            # Cleanup
            svc.delete_policy(_TENANT, result["id"])

    def test_duplicate_policy_rejected(self) -> None:
        with Session(engine) as s:
            svc = SoDService(s)
            r1 = svc.create_policy(_TENANT, "super_admin", "compliance_admin")
            assert "error" not in r1
            r2 = svc.create_policy(_TENANT, "compliance_admin", "super_admin")
            assert r2.get("error") == "duplicate"
            svc.delete_policy(_TENANT, r1["id"])

    def test_check_conflict_blocks_assignment(self) -> None:
        with Session(engine) as s:
            svc = SoDService(s)
            # Create test user with a role
            uid = _ensure_test_user(s, "sod-test@example.com")
            from datetime import UTC, datetime

            s.add(
                UserTenantRoleDB(
                    id=str(uuid.uuid4()),
                    user_id=uid,
                    tenant_id=_TENANT,
                    role="auditor",
                    assigned_by="test",
                    created_at_utc=datetime.now(UTC),
                    updated_at_utc=datetime.now(UTC),
                )
            )
            s.commit()
            # Create SoD policy
            pol = svc.create_policy(
                _TENANT,
                "auditor",
                "tenant_admin",
                severity="block",
            )
            # Check conflict when trying to assign tenant_admin
            conflicts = svc.check_conflicts(_TENANT, uid, "tenant_admin")
            assert len(conflicts) >= 1
            assert conflicts[0]["severity"] == "block"
            # Cleanup
            svc.delete_policy(_TENANT, pol["id"])

    def test_no_conflict_for_unrelated_role(self) -> None:
        with Session(engine) as s:
            svc = SoDService(s)
            uid = _ensure_test_user(s, "sod-ok@example.com")
            pol = svc.create_policy(_TENANT, "super_admin", "auditor", severity="block")
            # User has no role — viewer is being proposed
            conflicts = svc.check_conflicts(_TENANT, uid, "viewer")
            assert len(conflicts) == 0
            svc.delete_policy(_TENANT, pol["id"])

    def test_invalid_severity_rejected(self) -> None:
        with Session(engine) as s:
            svc = SoDService(s)
            result = svc.create_policy(_TENANT, "x", "y", severity="invalid")
            assert result.get("error") == "invalid_severity"


# ── Unit Tests: MFA Service ──────────────────────────────────────────────────


class TestMFAServiceUnit:
    def test_enroll_and_verify_totp(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-enroll@example.com")
            svc = MFAService(s)
            # Enroll
            result = svc.enroll_totp(uid)
            assert "error" not in result
            assert result["secret"]
            assert result["verified"] is False
            # Verify enrollment with current code
            code = _current_totp(result["secret"])
            verify_result = svc.verify_totp_enrollment(uid, code)
            assert verify_result["verified"] is True
            # Cleanup
            svc.reset_mfa(uid)

    def test_duplicate_enrollment_rejected(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-dup@example.com")
            svc = MFAService(s)
            r1 = svc.enroll_totp(uid)
            code = _current_totp(r1["secret"])
            svc.verify_totp_enrollment(uid, code)
            r2 = svc.enroll_totp(uid)
            assert r2.get("error") == "already_enrolled"
            svc.reset_mfa(uid)

    def test_invalid_totp_rejected(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-invalid@example.com")
            svc = MFAService(s)
            svc.enroll_totp(uid)
            result = svc.verify_totp_enrollment(uid, "000000")
            assert result.get("error") == "invalid_token"
            svc.reset_mfa(uid)

    def test_verify_totp_for_step_up(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-stepup@example.com")
            svc = MFAService(s)
            r = svc.enroll_totp(uid)
            code = _current_totp(r["secret"])
            svc.verify_totp_enrollment(uid, code)
            # Step-up verification
            code2 = _current_totp(r["secret"])
            assert svc.verify_totp(uid, code2) is True
            assert svc.verify_totp(uid, "999999") is False
            svc.reset_mfa(uid)

    def test_backup_codes_generation_and_use(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-backup@example.com")
            svc = MFAService(s)
            result = svc.generate_backup_codes(uid)
            assert result["count"] == 10
            assert len(result["codes"]) == 10
            # Verify one code
            code = result["codes"][0]
            assert svc.verify_backup_code(uid, code) is True
            # Same code cannot be reused
            assert svc.verify_backup_code(uid, code) is False
            # Wrong code fails
            assert svc.verify_backup_code(uid, "deadbeef") is False
            svc.reset_mfa(uid)

    def test_mfa_status(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-status@example.com")
            svc = MFAService(s)
            status = svc.get_mfa_status(uid)
            assert status["totp_enrolled"] is False
            assert status["backup_codes_remaining"] == 0
            r = svc.enroll_totp(uid)
            status = svc.get_mfa_status(uid)
            assert status["totp_pending_verification"] is True
            code = _current_totp(r["secret"])
            svc.verify_totp_enrollment(uid, code)
            status = svc.get_mfa_status(uid)
            assert status["totp_enrolled"] is True
            svc.generate_backup_codes(uid)
            status = svc.get_mfa_status(uid)
            assert status["backup_codes_remaining"] == 10
            svc.reset_mfa(uid)

    def test_step_up_challenge_totp(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-challenge@example.com")
            svc = MFAService(s)
            r = svc.enroll_totp(uid)
            code = _current_totp(r["secret"])
            svc.verify_totp_enrollment(uid, code)
            code2 = _current_totp(r["secret"])
            result = svc.step_up_challenge(uid, code2)
            assert result["verified"] is True
            assert result["method"] == "totp"
            svc.reset_mfa(uid)

    def test_step_up_challenge_backup_code(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-challenge-bc@example.com")
            svc = MFAService(s)
            codes = svc.generate_backup_codes(uid)
            result = svc.step_up_challenge(uid, codes["codes"][0])
            assert result["verified"] is True
            assert result["method"] == "backup_code"
            svc.reset_mfa(uid)

    def test_step_up_challenge_invalid(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-challenge-bad@example.com")
            svc = MFAService(s)
            result = svc.step_up_challenge(uid, "invalid")
            assert result["verified"] is False

    def test_reset_mfa_clears_all(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-reset@example.com")
            svc = MFAService(s)
            svc.enroll_totp(uid)
            svc.generate_backup_codes(uid)
            svc.reset_mfa(uid)
            status = svc.get_mfa_status(uid)
            assert status["totp_enrolled"] is False
            assert status["backup_codes_remaining"] == 0


# ── Unit Tests: Approval Workflow ────────────────────────────────────────────


class TestApprovalWorkflowUnit:
    def test_create_and_approve(self) -> None:
        with Session(engine) as s:
            uid1 = _ensure_test_user(s, "approver1@example.com")
            uid2 = _ensure_test_user(s, "requester1@example.com")
            svc = ApprovalWorkflowService(s)
            req = svc.create_request(
                _TENANT,
                "privileged_role_assignment",
                uid2,
                target_user_id=uid2,
                payload={"role": "tenant_admin"},
            )
            assert req["status"] == "pending"
            assert req["request_type"] == "privileged_role_assignment"
            # Approve by different user
            result = svc.decide(_TENANT, req["id"], uid1, "approved")
            assert result["status"] == "approved"
            assert result["approver_user_id"] == uid1

    def test_self_approval_blocked(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "self-approver@example.com")
            svc = ApprovalWorkflowService(s)
            req = svc.create_request(_TENANT, "privileged_role_assignment", uid)
            result = svc.decide(_TENANT, req["id"], uid, "approved")
            assert result.get("error") == "self_approval"
            assert "Self-approval" in result["detail"]

    def test_reject_request(self) -> None:
        with Session(engine) as s:
            uid1 = _ensure_test_user(s, "rejector@example.com")
            uid2 = _ensure_test_user(s, "req-reject@example.com")
            svc = ApprovalWorkflowService(s)
            req = svc.create_request(_TENANT, "unlock_user", uid2)
            result = svc.decide(_TENANT, req["id"], uid1, "rejected", decision_note="Not justified")
            assert result["status"] == "rejected"
            assert result["decision_note"] == "Not justified"

    def test_double_decision_blocked(self) -> None:
        with Session(engine) as s:
            uid1 = _ensure_test_user(s, "d-approver@example.com")
            uid2 = _ensure_test_user(s, "d-requester@example.com")
            svc = ApprovalWorkflowService(s)
            req = svc.create_request(_TENANT, "test", uid2)
            svc.decide(_TENANT, req["id"], uid1, "approved")
            result = svc.decide(_TENANT, req["id"], uid1, "approved")
            assert result.get("error") == "not_pending"

    def test_invalid_decision_rejected(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "inv-dec@example.com")
            svc = ApprovalWorkflowService(s)
            req = svc.create_request(_TENANT, "test", uid)
            result = svc.decide(_TENANT, req["id"], uid, "maybe")
            assert result.get("error") == "invalid_decision"

    def test_list_pending(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "pending-list@example.com")
            svc = ApprovalWorkflowService(s)
            svc.create_request(_TENANT, "test_pending", uid)
            pending = svc.list_pending(_TENANT)
            assert any(r["request_type"] == "test_pending" for r in pending)

    def test_expire_overdue(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "expire-test@example.com")
            svc = ApprovalWorkflowService(s)
            req = svc.create_request(_TENANT, "expire_test", uid, expiry_hours=0)
            import time

            time.sleep(0.1)
            count = svc.expire_overdue(_TENANT)
            assert count >= 1
            updated = svc.get_request(_TENANT, req["id"])
            assert updated["status"] == "expired"

    def test_get_request(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "get-req@example.com")
            svc = ApprovalWorkflowService(s)
            req = svc.create_request(_TENANT, "get_test", uid)
            fetched = svc.get_request(_TENANT, req["id"])
            assert fetched is not None
            assert fetched["id"] == req["id"]

    def test_not_found_returns_none(self) -> None:
        with Session(engine) as s:
            svc = ApprovalWorkflowService(s)
            assert svc.get_request(_TENANT, "nonexistent-id") is None


# ── Unit Tests: Privileged Action Events ─────────────────────────────────────


class TestPrivilegedActionEvents:
    def test_record_and_list(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "priv-actor@example.com")
            svc = PrivilegedActionService(s)
            event = svc.record(
                _TENANT,
                uid,
                "role_change",
                target_type="user",
                target_id=uid,
                detail={"from": "viewer", "to": "tenant_admin"},
                step_up_verified=True,
            )
            assert event["action"] == "role_change"
            assert event["step_up_verified"] is True
            events = svc.list_events(_TENANT, actor_user_id=uid)
            assert any(e["id"] == event["id"] for e in events)

    def test_step_up_actions_defined(self) -> None:
        assert "role_change" in STEP_UP_ACTIONS
        assert "sso_config_change" in STEP_UP_ACTIONS
        assert "scim_mapping_change" in STEP_UP_ACTIONS


# ── Integration Tests: API Endpoints ─────────────────────────────────────────


class TestSoDEndpoints:
    def test_create_sod_policy_api(self) -> None:
        resp = client.post(
            "/api/v1/enterprise/governance/sod-policies",
            json={
                "role_a": "super_admin",
                "role_b": "auditor",
                "description": "API test",
                "severity": "warn",
            },
            headers=_admin_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["severity"] == "warn"
        # Cleanup
        client.delete(
            f"/api/v1/enterprise/governance/sod-policies/{data['id']}",
            headers=_admin_headers(),
        )

    def test_list_sod_policies_api(self) -> None:
        resp = client.get(
            "/api/v1/enterprise/governance/sod-policies",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_sod_policy_requires_permission(self) -> None:
        resp = client.post(
            "/api/v1/enterprise/governance/sod-policies",
            json={"role_a": "x", "role_b": "y"},
            headers={**_headers(), "x-opa-user-role": "viewer"},
        )
        assert resp.status_code == 403


class TestMFAEndpoints:
    def test_mfa_status_api(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "mfa-api-status@example.com")
        resp = client.get(
            f"/api/v1/enterprise/governance/mfa/status/{uid}",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "totp_enrolled" in data

    def test_mfa_requires_permission(self) -> None:
        resp = client.get(
            "/api/v1/enterprise/governance/mfa/status/fake-id",
            headers={**_headers(), "x-opa-user-role": "viewer"},
        )
        assert resp.status_code == 403


class TestApprovalEndpoints:
    def test_create_approval_api(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "appr-api@example.com")
        resp = client.post(
            "/api/v1/enterprise/governance/approvals",
            json={"request_type": "privileged_role_assignment"},
            params={"requester_user_id": uid},
            headers=_admin_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"

    def test_list_pending_api(self) -> None:
        resp = client.get(
            "/api/v1/enterprise/governance/approvals/pending",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_self_approval_api(self) -> None:
        with Session(engine) as s:
            uid = _ensure_test_user(s, "self-appr-api@example.com")
        resp = client.post(
            "/api/v1/enterprise/governance/approvals",
            json={"request_type": "test_self"},
            params={"requester_user_id": uid},
            headers=_admin_headers(),
        )
        req_id = resp.json()["id"]
        resp2 = client.post(
            f"/api/v1/enterprise/governance/approvals/{req_id}/decide",
            json={"decision": "approved"},
            params={"approver_user_id": uid},
            headers=_admin_headers(),
        )
        assert resp2.status_code == 403
        assert "Self-approval" in resp2.json()["detail"]

    def test_approval_requires_permission(self) -> None:
        resp = client.get(
            "/api/v1/enterprise/governance/approvals",
            headers={**_headers(), "x-opa-user-role": "viewer"},
        )
        assert resp.status_code == 403


class TestPrivilegedEventsEndpoints:
    def test_list_events_api(self) -> None:
        resp = client.get(
            "/api/v1/enterprise/governance/privileged-events",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_auditor_can_view_events(self) -> None:
        resp = client.get(
            "/api/v1/enterprise/governance/privileged-events",
            headers={**_headers(), "x-opa-user-role": "auditor"},
        )
        assert resp.status_code == 200

    def test_viewer_cannot_view_events(self) -> None:
        resp = client.get(
            "/api/v1/enterprise/governance/privileged-events",
            headers={**_headers(), "x-opa-user-role": "viewer"},
        )
        assert resp.status_code == 403


# ── Negative Tests ───────────────────────────────────────────────────────────


class TestNegativeGovernance:
    def test_step_up_bypass_blocked(self) -> None:
        """Step-up with invalid token must fail."""
        with Session(engine) as s:
            uid = _ensure_test_user(s, "bypass-test@example.com")
        resp = client.post(
            "/api/v1/enterprise/governance/mfa/step-up",
            json={"token": "invalid", "action": "role_change"},
            params={"user_id": uid},
            headers=_admin_headers(),
        )
        assert resp.status_code == 401

    def test_self_approval_blocked_api(self) -> None:
        """Self-approval must be blocked at API level."""
        with Session(engine) as s:
            uid = _ensure_test_user(s, "neg-selfappr@example.com")
        resp = client.post(
            "/api/v1/enterprise/governance/approvals",
            json={"request_type": "test"},
            params={"requester_user_id": uid},
            headers=_admin_headers(),
        )
        req_id = resp.json()["id"]
        resp2 = client.post(
            f"/api/v1/enterprise/governance/approvals/{req_id}/decide",
            json={"decision": "approved"},
            params={"approver_user_id": uid},
            headers=_admin_headers(),
        )
        assert resp2.status_code == 403

    def test_conflicting_role_assignment_detected(self) -> None:
        """SoD check must detect conflicting role assignments."""
        with Session(engine) as s:
            svc = SoDService(s)
            uid = _ensure_test_user(s, "conflict-detect@example.com")
            from datetime import UTC, datetime

            s.add(
                UserTenantRoleDB(
                    id=str(uuid.uuid4()),
                    user_id=uid,
                    tenant_id=_TENANT,
                    role="compliance_admin",
                    assigned_by="test",
                    created_at_utc=datetime.now(UTC),
                    updated_at_utc=datetime.now(UTC),
                )
            )
            s.commit()
            pol = svc.create_policy(
                _TENANT,
                "compliance_admin",
                "auditor",
                severity="block",
                description="Admin+Auditor conflict",
            )
            conflicts = svc.check_conflicts(_TENANT, uid, "auditor")
            assert len(conflicts) >= 1
            assert conflicts[0]["severity"] == "block"
            svc.delete_policy(_TENANT, pol["id"])

    def test_invalid_mfa_token_blocked(self) -> None:
        """Invalid MFA token must fail enrollment verification."""
        with Session(engine) as s:
            uid = _ensure_test_user(s, "bad-mfa@example.com")
            svc = MFAService(s)
            svc.enroll_totp(uid)
            result = svc.verify_totp_enrollment(uid, "000000")
            assert result.get("error") == "invalid_token"
            svc.reset_mfa(uid)
