"""Enterprise Governance services — SoD, MFA, Approval Workflows, Privileged Access.

Extends the existing IAM foundation (PR #203/#205) with:
- Segregation of Duties evaluation & policy management
- MFA enrollment / verification / reset (TOTP + backup codes)
- Approval workflow engine with 4-eye principle and no self-approval
- Privileged action audit logging
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import struct
import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import (
    ApprovalRequestDB,
    MFABackupCodeDB,
    MFAFactorDB,
    PrivilegedActionEventDB,
    SoDPolicyDB,
    UserTenantRoleDB,
)
from app.services.enterprise_iam_service import PRIVILEGED_ROLES

logger = logging.getLogger(__name__)

# ── Privileged Access Constants ──────────────────────────────────────────────

# Actions that require step-up MFA verification
STEP_UP_ACTIONS = frozenset(
    {
        "role_change",
        "sso_config_change",
        "scim_mapping_change",
        "sensitive_data_export",
        "privileged_admin_action",
        "sod_rule_change",
        "approval_config_change",
    }
)

# Approval request expiry (hours)
APPROVAL_EXPIRY_HOURS = 72

# Number of backup codes generated per user
BACKUP_CODE_COUNT = 10


# ── Segregation of Duties (SoD) Service ─────────────────────────────────────


class SoDService:
    """Central SoD policy management and conflict evaluation."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_policy(
        self,
        tenant_id: str,
        role_a: str,
        role_b: str,
        *,
        description: str | None = None,
        severity: str = "block",
    ) -> dict:
        """Create a SoD rule that marks two roles as conflicting."""
        if severity not in ("block", "warn"):
            return {"error": "invalid_severity", "detail": "severity must be 'block' or 'warn'"}
        # Normalise pair (alphabetical) to avoid (a,b) and (b,a) duplicates
        r_a, r_b = sorted([role_a.lower(), role_b.lower()])
        existing = self._session.execute(
            select(SoDPolicyDB).where(
                SoDPolicyDB.tenant_id == tenant_id,
                SoDPolicyDB.role_a == r_a,
                SoDPolicyDB.role_b == r_b,
            )
        ).scalar_one_or_none()
        if existing is not None:
            return {"error": "duplicate", "detail": "SoD policy already exists for this pair"}
        now = datetime.now(UTC)
        policy = SoDPolicyDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            role_a=r_a,
            role_b=r_b,
            description=description,
            severity=severity,
            enabled=True,
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(policy)
        self._session.commit()
        self._session.refresh(policy)
        return self._to_dict(policy)

    def list_policies(self, tenant_id: str) -> list[dict]:
        rows = (
            self._session.execute(select(SoDPolicyDB).where(SoDPolicyDB.tenant_id == tenant_id))
            .scalars()
            .all()
        )
        return [self._to_dict(r) for r in rows]

    def delete_policy(self, tenant_id: str, policy_id: str) -> bool:
        policy = self._session.execute(
            select(SoDPolicyDB).where(
                SoDPolicyDB.id == policy_id,
                SoDPolicyDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if policy is None:
            return False
        self._session.delete(policy)
        self._session.commit()
        return True

    def check_conflicts(
        self,
        tenant_id: str,
        user_id: str,
        proposed_role: str,
    ) -> list[dict]:
        """Check if assigning *proposed_role* to *user_id* violates any SoD rules.

        Returns a list of conflict dicts (empty means no conflicts).
        """
        # Current roles of this user within the tenant
        existing_roles_rows = (
            self._session.execute(
                select(UserTenantRoleDB).where(
                    UserTenantRoleDB.user_id == user_id,
                    UserTenantRoleDB.tenant_id == tenant_id,
                )
            )
            .scalars()
            .all()
        )
        current_roles = {r.role.lower() for r in existing_roles_rows}
        proposed = proposed_role.lower()

        # All enabled policies for this tenant
        policies = (
            self._session.execute(
                select(SoDPolicyDB).where(
                    SoDPolicyDB.tenant_id == tenant_id,
                    SoDPolicyDB.enabled.is_(True),
                )
            )
            .scalars()
            .all()
        )
        conflicts: list[dict] = []
        for p in policies:
            # Check if proposed + any existing role match the policy pair
            pair = {p.role_a, p.role_b}
            if proposed in pair:
                other = (pair - {proposed}).pop() if len(pair) > 1 else proposed
                if other in current_roles or (proposed == other and proposed in current_roles):
                    conflicts.append(
                        {
                            "policy_id": p.id,
                            "role_a": p.role_a,
                            "role_b": p.role_b,
                            "severity": p.severity,
                            "description": p.description,
                        }
                    )
        return conflicts

    @staticmethod
    def _to_dict(p: SoDPolicyDB) -> dict:
        return {
            "id": p.id,
            "tenant_id": p.tenant_id,
            "role_a": p.role_a,
            "role_b": p.role_b,
            "description": p.description,
            "severity": p.severity,
            "enabled": p.enabled,
            "created_at_utc": p.created_at_utc.isoformat() if p.created_at_utc else None,
        }


# ── MFA Service (TOTP + Backup Codes) ───────────────────────────────────────

# Lightweight RFC 6238 TOTP — we only do the math, no third-party lib needed.
_TOTP_PERIOD = 30
_TOTP_DIGITS = 6


def _generate_totp_secret() -> str:
    """Return a 20-byte hex-encoded random secret for TOTP."""
    return secrets.token_hex(20)


def _compute_totp(secret_hex: str, counter: int) -> str:
    """RFC 4226 HOTP for a given counter, formatted to *_TOTP_DIGITS* digits."""
    key = bytes.fromhex(secret_hex)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**_TOTP_DIGITS)).zfill(_TOTP_DIGITS)


def _current_totp(secret_hex: str) -> str:
    """Return the current TOTP code for this second."""
    counter = int(time.time()) // _TOTP_PERIOD
    return _compute_totp(secret_hex, counter)


def _verify_totp(secret_hex: str, token: str, *, window: int = 1) -> bool:
    """Verify *token* against the current TOTP ±window steps."""
    counter = int(time.time()) // _TOTP_PERIOD
    for offset in range(-window, window + 1):
        if hmac.compare_digest(_compute_totp(secret_hex, counter + offset), token):
            return True
    return False


class MFAService:
    """MFA enrollment / verification / reset (TOTP + backup codes)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def enroll_totp(self, user_id: str) -> dict:
        """Create a new TOTP factor for a user (must be verified before active use)."""
        # Check if already enrolled
        existing = self._session.execute(
            select(MFAFactorDB).where(
                MFAFactorDB.user_id == user_id,
                MFAFactorDB.factor_type == "totp",
                MFAFactorDB.enabled.is_(True),
            )
        ).scalar_one_or_none()
        if existing is not None and existing.verified:
            return {"error": "already_enrolled", "detail": "TOTP factor already active"}

        # Remove any unverified factor before creating new one
        if existing is not None and not existing.verified:
            self._session.delete(existing)
            self._session.flush()

        secret = _generate_totp_secret()
        now = datetime.now(UTC)
        factor = MFAFactorDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            factor_type="totp",
            secret_encrypted=secret,  # In prod: encrypt-at-rest via KMS
            verified=False,
            enabled=True,
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(factor)
        self._session.commit()
        self._session.refresh(factor)
        return {
            "factor_id": factor.id,
            "secret": secret,
            "factor_type": "totp",
            "verified": False,
        }

    def verify_totp_enrollment(self, user_id: str, token: str) -> dict:
        """Verify the initial TOTP enrollment by providing a valid code."""
        factor = self._session.execute(
            select(MFAFactorDB).where(
                MFAFactorDB.user_id == user_id,
                MFAFactorDB.factor_type == "totp",
                MFAFactorDB.enabled.is_(True),
            )
        ).scalar_one_or_none()
        if factor is None:
            return {"error": "no_factor", "detail": "No TOTP factor found"}
        if factor.verified:
            return {"error": "already_verified", "detail": "Factor already verified"}
        if not _verify_totp(factor.secret_encrypted, token):
            return {"error": "invalid_token", "detail": "Invalid TOTP code"}
        factor.verified = True
        factor.updated_at_utc = datetime.now(UTC)
        self._session.commit()
        return {"factor_id": factor.id, "verified": True}

    def verify_totp(self, user_id: str, token: str) -> bool:
        """Verify a TOTP code for step-up / login MFA challenge."""
        factor = self._session.execute(
            select(MFAFactorDB).where(
                MFAFactorDB.user_id == user_id,
                MFAFactorDB.factor_type == "totp",
                MFAFactorDB.verified.is_(True),
                MFAFactorDB.enabled.is_(True),
            )
        ).scalar_one_or_none()
        if factor is None:
            return False
        return _verify_totp(factor.secret_encrypted, token)

    def get_mfa_status(self, user_id: str) -> dict:
        """Return the MFA enrollment status for a user."""
        factor = self._session.execute(
            select(MFAFactorDB).where(
                MFAFactorDB.user_id == user_id,
                MFAFactorDB.factor_type == "totp",
                MFAFactorDB.enabled.is_(True),
            )
        ).scalar_one_or_none()
        backup_count = (
            self._session.execute(
                select(MFABackupCodeDB).where(
                    MFABackupCodeDB.user_id == user_id,
                    MFABackupCodeDB.used.is_(False),
                )
            )
            .scalars()
            .all()
        )
        return {
            "totp_enrolled": factor is not None and factor.verified,
            "totp_pending_verification": factor is not None and not factor.verified,
            "backup_codes_remaining": len(backup_count),
        }

    def generate_backup_codes(self, user_id: str) -> dict:
        """Generate a new set of backup codes (invalidates previous ones)."""
        # Delete old codes
        old_codes = (
            self._session.execute(select(MFABackupCodeDB).where(MFABackupCodeDB.user_id == user_id))
            .scalars()
            .all()
        )
        for c in old_codes:
            self._session.delete(c)
        self._session.flush()

        now = datetime.now(UTC)
        codes: list[str] = []
        for _ in range(BACKUP_CODE_COUNT):
            raw_code = secrets.token_hex(4)  # 8 hex chars
            code_hash = hashlib.sha256(raw_code.encode()).hexdigest()
            self._session.add(
                MFABackupCodeDB(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    code_hash=code_hash,
                    used=False,
                    created_at_utc=now,
                )
            )
            codes.append(raw_code)
        self._session.commit()
        return {"codes": codes, "count": len(codes)}

    def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify and consume a single-use backup code."""
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        bc = self._session.execute(
            select(MFABackupCodeDB).where(
                MFABackupCodeDB.user_id == user_id,
                MFABackupCodeDB.code_hash == code_hash,
                MFABackupCodeDB.used.is_(False),
            )
        ).scalar_one_or_none()
        if bc is None:
            return False
        bc.used = True
        self._session.commit()
        return True

    def reset_mfa(self, user_id: str) -> dict:
        """Remove all MFA factors and backup codes for a user (admin-only)."""
        factors = (
            self._session.execute(select(MFAFactorDB).where(MFAFactorDB.user_id == user_id))
            .scalars()
            .all()
        )
        for f in factors:
            self._session.delete(f)
        codes = (
            self._session.execute(select(MFABackupCodeDB).where(MFABackupCodeDB.user_id == user_id))
            .scalars()
            .all()
        )
        for c in codes:
            self._session.delete(c)
        self._session.commit()
        return {"user_id": user_id, "mfa_reset": True}

    def step_up_challenge(self, user_id: str, token: str) -> dict:
        """Verify a step-up MFA challenge (TOTP or backup code).

        Returns success/failure dict — callers use this before executing sensitive actions.
        """
        if self.verify_totp(user_id, token):
            return {"verified": True, "method": "totp"}
        if self.verify_backup_code(user_id, token):
            return {"verified": True, "method": "backup_code"}
        return {"verified": False, "detail": "Invalid MFA token"}


# ── Approval Workflow Service ────────────────────────────────────────────────


class ApprovalWorkflowService:
    """4-eye-principle approval workflow for sensitive operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_request(
        self,
        tenant_id: str,
        request_type: str,
        requester_user_id: str,
        *,
        target_user_id: str | None = None,
        payload: dict | None = None,
        expiry_hours: int = APPROVAL_EXPIRY_HOURS,
    ) -> dict:
        now = datetime.now(UTC)
        req = ApprovalRequestDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            request_type=request_type,
            requester_user_id=requester_user_id,
            target_user_id=target_user_id,
            payload=json.dumps(payload) if payload else None,
            status="pending",
            expires_at_utc=now + timedelta(hours=expiry_hours),
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(req)
        self._session.commit()
        self._session.refresh(req)
        return self._to_dict(req)

    def decide(
        self,
        tenant_id: str,
        request_id: str,
        approver_user_id: str,
        decision: str,
        *,
        decision_note: str | None = None,
    ) -> dict:
        """Approve or reject a pending request.

        Enforces no self-approval: requester cannot approve their own request.
        """
        if decision not in ("approved", "rejected"):
            return {"error": "invalid_decision", "detail": "decision must be approved or rejected"}
        req = self._session.execute(
            select(ApprovalRequestDB).where(
                ApprovalRequestDB.id == request_id,
                ApprovalRequestDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if req is None:
            return {"error": "not_found", "detail": "Approval request not found"}
        if req.status not in ("pending", "requested"):
            return {"error": "not_pending", "detail": f"Request is already {req.status}"}
        # Enforce no self-approval (4-eye principle)
        if req.requester_user_id == approver_user_id:
            return {"error": "self_approval", "detail": "Self-approval is not permitted"}
        # Check expiry (handle naive datetimes from SQLite)
        if req.expires_at_utc:
            exp = req.expires_at_utc
            now_utc = datetime.now(UTC)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            if now_utc > exp:
                req.status = "expired"
                req.updated_at_utc = datetime.now(UTC)
                self._session.commit()
                return {"error": "expired", "detail": "Approval request has expired"}
        now = datetime.now(UTC)
        req.status = decision
        req.approver_user_id = approver_user_id
        req.decision_note = decision_note
        req.decided_at_utc = now
        req.updated_at_utc = now
        self._session.commit()
        self._session.refresh(req)
        return self._to_dict(req)

    def list_pending(self, tenant_id: str) -> list[dict]:
        """List all pending/requested approval requests for a tenant."""
        rows = (
            self._session.execute(
                select(ApprovalRequestDB)
                .where(
                    ApprovalRequestDB.tenant_id == tenant_id,
                    ApprovalRequestDB.status.in_(["pending", "requested"]),
                )
                .order_by(ApprovalRequestDB.created_at_utc.desc())
            )
            .scalars()
            .all()
        )
        return [self._to_dict(r) for r in rows]

    def list_all(self, tenant_id: str, *, status_filter: str | None = None) -> list[dict]:
        stmt = select(ApprovalRequestDB).where(ApprovalRequestDB.tenant_id == tenant_id)
        if status_filter:
            stmt = stmt.where(ApprovalRequestDB.status == status_filter)
        stmt = stmt.order_by(ApprovalRequestDB.created_at_utc.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_dict(r) for r in rows]

    def get_request(self, tenant_id: str, request_id: str) -> dict | None:
        req = self._session.execute(
            select(ApprovalRequestDB).where(
                ApprovalRequestDB.id == request_id,
                ApprovalRequestDB.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if req is None:
            return None
        return self._to_dict(req)

    def expire_overdue(self, tenant_id: str) -> int:
        """Mark expired approval requests. Returns count of newly expired."""
        now = datetime.now(UTC)
        rows = (
            self._session.execute(
                select(ApprovalRequestDB).where(
                    ApprovalRequestDB.tenant_id == tenant_id,
                    ApprovalRequestDB.status.in_(["pending", "requested"]),
                    ApprovalRequestDB.expires_at_utc < now,
                )
            )
            .scalars()
            .all()
        )
        for r in rows:
            r.status = "expired"
            r.updated_at_utc = now
        self._session.commit()
        return len(rows)

    @staticmethod
    def _to_dict(req: ApprovalRequestDB) -> dict:
        return {
            "id": req.id,
            "tenant_id": req.tenant_id,
            "request_type": req.request_type,
            "requester_user_id": req.requester_user_id,
            "target_user_id": req.target_user_id,
            "payload": json.loads(req.payload) if req.payload else None,
            "status": req.status,
            "approver_user_id": req.approver_user_id,
            "decision_note": req.decision_note,
            "decided_at_utc": req.decided_at_utc.isoformat() if req.decided_at_utc else None,
            "expires_at_utc": req.expires_at_utc.isoformat() if req.expires_at_utc else None,
            "created_at_utc": req.created_at_utc.isoformat() if req.created_at_utc else None,
        }


# ── Privileged Action Audit Service ─────────────────────────────────────────


class PrivilegedActionService:
    """Audit logging for privileged actions (governance-grade traceability)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        tenant_id: str,
        actor_user_id: str,
        action: str,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        detail: dict | None = None,
        step_up_verified: bool = False,
        approval_id: str | None = None,
    ) -> dict:
        now = datetime.now(UTC)
        event = PrivilegedActionEventDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=json.dumps(detail) if detail else None,
            step_up_verified=step_up_verified,
            approval_id=approval_id,
            created_at_utc=now,
        )
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return self._to_dict(event)

    def list_events(
        self,
        tenant_id: str,
        *,
        actor_user_id: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        stmt = select(PrivilegedActionEventDB).where(PrivilegedActionEventDB.tenant_id == tenant_id)
        if actor_user_id:
            stmt = stmt.where(PrivilegedActionEventDB.actor_user_id == actor_user_id)
        stmt = stmt.order_by(PrivilegedActionEventDB.created_at_utc.desc()).limit(limit)
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_dict(r) for r in rows]

    @staticmethod
    def _to_dict(event: PrivilegedActionEventDB) -> dict:
        return {
            "id": event.id,
            "tenant_id": event.tenant_id,
            "actor_user_id": event.actor_user_id,
            "action": event.action,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "detail": json.loads(event.detail) if event.detail else None,
            "step_up_verified": event.step_up_verified,
            "approval_id": event.approval_id,
            "created_at_utc": event.created_at_utc.isoformat() if event.created_at_utc else None,
        }


def is_privileged_role(role: str) -> bool:
    """Check whether a role is considered privileged."""
    return role.lower() in PRIVILEGED_ROLES
