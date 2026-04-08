"""User data-access layer (DSGVO data-sparse, tenant-isolated roles)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import UserDB, UserTenantRoleDB


class UserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── CREATE ────────────────────────────────────────────────────────
    def create_user(
        self,
        email: str,
        password_hash: str,
        display_name: str | None = None,
        company: str | None = None,
        language: str = "de",
        timezone: str = "Europe/Berlin",
        email_verification_token: str | None = None,
    ) -> UserDB:
        now = datetime.now(UTC)
        user = UserDB(
            id=str(uuid.uuid4()),
            email=email.strip().lower(),
            password_hash=password_hash,
            display_name=display_name,
            company=company,
            language=language,
            timezone=timezone,
            email_verification_token=email_verification_token,
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    # ── READ ──────────────────────────────────────────────────────────
    def get_by_email(self, email: str) -> UserDB | None:
        stmt = select(UserDB).where(UserDB.email == email.strip().lower())
        return self._session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, user_id: str) -> UserDB | None:
        stmt = select(UserDB).where(UserDB.id == user_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def get_by_verification_token(self, token: str) -> UserDB | None:
        stmt = select(UserDB).where(UserDB.email_verification_token == token)
        return self._session.execute(stmt).scalar_one_or_none()

    def get_by_password_reset_token(self, token: str) -> UserDB | None:
        stmt = select(UserDB).where(UserDB.password_reset_token == token)
        return self._session.execute(stmt).scalar_one_or_none()

    # ── UPDATE ────────────────────────────────────────────────────────
    def mark_email_verified(self, user_id: str) -> bool:
        user = self.get_by_id(user_id)
        if user is None:
            return False
        user.email_verified = True
        user.email_verification_token = None
        user.updated_at_utc = datetime.now(UTC)
        self._session.commit()
        return True

    def set_password_reset_token(self, user_id: str, token: str, expires: datetime) -> bool:
        user = self.get_by_id(user_id)
        if user is None:
            return False
        user.password_reset_token = token
        user.password_reset_expires = expires
        user.updated_at_utc = datetime.now(UTC)
        self._session.commit()
        return True

    def reset_password(self, user_id: str, password_hash: str) -> bool:
        user = self.get_by_id(user_id)
        if user is None:
            return False
        user.password_hash = password_hash
        user.password_reset_token = None
        user.password_reset_expires = None
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at_utc = datetime.now(UTC)
        self._session.commit()
        return True

    def increment_failed_login(self, user_id: str) -> int:
        user = self.get_by_id(user_id)
        if user is None:
            return 0
        user.failed_login_attempts += 1
        user.updated_at_utc = datetime.now(UTC)
        self._session.commit()
        return user.failed_login_attempts

    def clear_failed_logins(self, user_id: str) -> None:
        user = self.get_by_id(user_id)
        if user is None:
            return
        user.failed_login_attempts = 0
        user.locked_until = None
        user.updated_at_utc = datetime.now(UTC)
        self._session.commit()

    def lock_user(self, user_id: str, until: datetime) -> None:
        user = self.get_by_id(user_id)
        if user is None:
            return
        user.locked_until = until
        user.updated_at_utc = datetime.now(UTC)
        self._session.commit()

    def update_profile(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        company: str | None = None,
        language: str | None = None,
        timezone: str | None = None,
    ) -> UserDB | None:
        user = self.get_by_id(user_id)
        if user is None:
            return None
        if display_name is not None:
            user.display_name = display_name
        if company is not None:
            user.company = company
        if language is not None:
            user.language = language
        if timezone is not None:
            user.timezone = timezone
        user.updated_at_utc = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(user)
        return user

    # ── TENANT ROLES ──────────────────────────────────────────────────
    def assign_role(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        assigned_by: str | None = None,
    ) -> UserTenantRoleDB:
        now = datetime.now(UTC)
        existing = self.get_role(user_id, tenant_id)
        if existing:
            existing.role = role
            existing.assigned_by = assigned_by
            existing.updated_at_utc = now
            self._session.commit()
            self._session.refresh(existing)
            return existing
        assignment = UserTenantRoleDB(
            id=str(uuid.uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            assigned_by=assigned_by,
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(assignment)
        self._session.commit()
        self._session.refresh(assignment)
        return assignment

    def get_role(self, user_id: str, tenant_id: str) -> UserTenantRoleDB | None:
        stmt = select(UserTenantRoleDB).where(
            UserTenantRoleDB.user_id == user_id,
            UserTenantRoleDB.tenant_id == tenant_id,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_roles_for_user(self, user_id: str) -> list[UserTenantRoleDB]:
        stmt = select(UserTenantRoleDB).where(UserTenantRoleDB.user_id == user_id)
        return list(self._session.execute(stmt).scalars().all())

    def list_users_for_tenant(self, tenant_id: str) -> list[UserTenantRoleDB]:
        stmt = select(UserTenantRoleDB).where(UserTenantRoleDB.tenant_id == tenant_id)
        return list(self._session.execute(stmt).scalars().all())
