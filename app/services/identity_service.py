"""Identity service — registration, verification, login, password-reset, profile."""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from app.repositories.users import UserRepository
from app.services.sbs_domain_auto_admin import resolve_auto_role

logger = logging.getLogger(__name__)

# Password policy constants
MIN_PASSWORD_LENGTH = 10
MAX_FAILED_LOGINS = 5
LOCKOUT_DURATION_MINUTES = 15
PASSWORD_RESET_TOKEN_TTL_HOURS = 1


def _hash_password(password: str) -> str:
    """SHA-256 password hash (production would use bcrypt/argon2)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    return _hash_password(password) == hashed


def _generate_token() -> str:
    return secrets.token_urlsafe(48)


def validate_password_strength(password: str) -> str | None:
    """Return error message if password is weak, else None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_upper and has_lower and has_digit):
        return "Password must contain uppercase, lowercase, and digit characters"
    return None


class IdentityService:
    def __init__(self, user_repo: UserRepository) -> None:
        self._repo = user_repo

    def register(
        self,
        email: str,
        password: str,
        display_name: str | None = None,
        company: str | None = None,
        language: str = "de",
        timezone_str: str = "Europe/Berlin",
    ) -> dict:
        """Register a new user. Returns dict with user info and verification token."""
        email_norm = email.strip().lower()
        existing = self._repo.get_by_email(email_norm)
        if existing is not None:
            return {"error": "email_taken", "detail": "Email already registered"}

        pw_error = validate_password_strength(password)
        if pw_error:
            return {"error": "weak_password", "detail": pw_error}

        verification_token = _generate_token()
        pw_hash = _hash_password(password)
        user = self._repo.create_user(
            email=email_norm,
            password_hash=pw_hash,
            display_name=display_name,
            company=company,
            language=language,
            timezone=timezone_str,
            email_verification_token=verification_token,
        )
        return {
            "user_id": user.id,
            "email": user.email,
            "email_verified": False,
            "verification_token": verification_token,
        }

    def verify_email(self, token: str) -> dict:
        """Verify email via token. Returns user info or error."""
        user = self._repo.get_by_verification_token(token)
        if user is None:
            return {"error": "invalid_token", "detail": "Verification token invalid or expired"}
        self._repo.mark_email_verified(user.id)
        # Check SBS auto-admin after verification
        auto_role = resolve_auto_role(user.email, email_verified=True)
        return {
            "user_id": user.id,
            "email": user.email,
            "email_verified": True,
            "auto_role": auto_role.value if auto_role else None,
        }

    def login(self, email: str, password: str) -> dict:
        """Authenticate user. Returns user info or error."""
        email_norm = email.strip().lower()
        user = self._repo.get_by_email(email_norm)
        if user is None:
            return {"error": "invalid_credentials", "detail": "Invalid email or password"}

        if not user.is_active:
            return {"error": "account_disabled", "detail": "Account is disabled"}

        # Check lockout
        if user.locked_until:
            locked = user.locked_until
            if hasattr(locked, "tzinfo") and locked.tzinfo is None:
                locked = locked.replace(tzinfo=UTC)
            if locked > datetime.now(UTC):
                return {
                    "error": "account_locked",
                    "detail": "Account temporarily locked due to too many failed attempts",
                }

        if not _verify_password(password, user.password_hash):
            attempts = self._repo.increment_failed_login(user.id)
            if attempts >= MAX_FAILED_LOGINS:
                lockout = datetime.now(UTC) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                self._repo.lock_user(user.id, lockout)
                return {
                    "error": "account_locked",
                    "detail": "Account locked due to too many failed attempts",
                }
            return {"error": "invalid_credentials", "detail": "Invalid email or password"}

        self._repo.clear_failed_logins(user.id)
        roles = self._repo.list_roles_for_user(user.id)
        return {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "email_verified": user.email_verified,
            "roles": [{"tenant_id": r.tenant_id, "role": r.role} for r in roles],
        }

    def request_password_reset(self, email: str) -> dict:
        """Generate password reset token. Always returns success to not leak user existence."""
        email_norm = email.strip().lower()
        user = self._repo.get_by_email(email_norm)
        if user is None:
            return {"message": "If the email exists, a reset link has been sent"}

        token = _generate_token()
        expires = datetime.now(UTC) + timedelta(hours=PASSWORD_RESET_TOKEN_TTL_HOURS)
        self._repo.set_password_reset_token(user.id, token, expires)
        return {
            "message": "If the email exists, a reset link has been sent",
            "reset_token": token,
        }

    def reset_password(self, token: str, new_password: str) -> dict:
        """Reset password using token."""
        user = self._repo.get_by_password_reset_token(token)
        if user is None:
            return {"error": "invalid_token", "detail": "Reset token invalid or expired"}

        if user.password_reset_expires:
            expires = user.password_reset_expires
            if hasattr(expires, "tzinfo") and expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if expires < datetime.now(UTC):
                return {"error": "token_expired", "detail": "Reset token has expired"}

        pw_error = validate_password_strength(new_password)
        if pw_error:
            return {"error": "weak_password", "detail": pw_error}

        pw_hash = _hash_password(new_password)
        self._repo.reset_password(user.id, pw_hash)
        return {"message": "Password has been reset successfully", "user_id": user.id}

    def get_profile(self, user_id: str) -> dict | None:
        """Return user profile data (DSGVO data-sparse)."""
        user = self._repo.get_by_id(user_id)
        if user is None:
            return None
        roles = self._repo.list_roles_for_user(user_id)
        return {
            "user_id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "company": user.company,
            "language": user.language,
            "timezone": user.timezone,
            "email_verified": user.email_verified,
            "is_active": user.is_active,
            "roles": [{"tenant_id": r.tenant_id, "role": r.role} for r in roles],
            "created_at_utc": user.created_at_utc.isoformat() if user.created_at_utc else None,
        }

    def update_profile(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        company: str | None = None,
        language: str | None = None,
        timezone_str: str | None = None,
    ) -> dict | None:
        user = self._repo.update_profile(
            user_id,
            display_name=display_name,
            company=company,
            language=language,
            timezone=timezone_str,
        )
        if user is None:
            return None
        return self.get_profile(user_id)

    def assign_role(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        assigned_by: str | None = None,
    ) -> dict:
        """Assign a tenant-specific role to a user."""
        user = self._repo.get_by_id(user_id)
        if user is None:
            return {"error": "user_not_found", "detail": "User not found"}
        assignment = self._repo.assign_role(user_id, tenant_id, role, assigned_by)
        return {
            "user_id": user_id,
            "tenant_id": assignment.tenant_id,
            "role": assignment.role,
            "assigned_by": assignment.assigned_by,
        }

    def apply_sbs_auto_admin(self, user_id: str, tenant_id: str) -> dict | None:
        """Apply SBS domain auto-admin if conditions are met. Returns role info or None."""
        user = self._repo.get_by_id(user_id)
        if user is None:
            return None
        auto_role = resolve_auto_role(user.email, email_verified=user.email_verified)
        if auto_role is None:
            return None
        assignment = self._repo.assign_role(
            user_id, tenant_id, auto_role.value, assigned_by="system:sbs_auto_admin"
        )
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": assignment.role,
            "auto_assigned": True,
        }
