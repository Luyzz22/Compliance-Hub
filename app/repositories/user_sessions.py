"""Persistence for revocable, tenant-bound user sessions."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import UserSessionDB
from app.security import hash_api_key


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class UserSessionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        user_id: str,
        tenant_id: str,
        role: str,
        auth_method: str,
        ttl: timedelta,
    ) -> tuple[UserSessionDB, str]:
        now = datetime.now(UTC)
        raw_token = f"chs_{secrets.token_urlsafe(48)}"
        row = UserSessionDB(
            id=str(uuid.uuid4()),
            token_hash=hash_api_key(raw_token),
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            auth_method=auth_method,
            created_at_utc=now,
            last_seen_at_utc=now,
            expires_at_utc=now + ttl,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row, raw_token

    def resolve(self, raw_token: str, *, touch: bool = True) -> UserSessionDB | None:
        token = str(raw_token).strip()
        if not token:
            return None
        stmt = select(UserSessionDB).where(UserSessionDB.token_hash == hash_api_key(token))
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None or row.revoked_at_utc is not None:
            return None
        now = datetime.now(UTC)
        if _as_utc(row.expires_at_utc) <= now:
            return None
        if touch and now - _as_utc(row.last_seen_at_utc) >= timedelta(minutes=5):
            row.last_seen_at_utc = now
            self._session.commit()
        return row

    def revoke(self, raw_token: str, *, reason: str = "logout") -> bool:
        row = self.resolve(raw_token, touch=False)
        if row is None:
            return False
        row.revoked_at_utc = datetime.now(UTC)
        row.revoked_reason = reason[:128]
        self._session.commit()
        return True

    def revoke_all_for_user(self, user_id: str, *, reason: str) -> int:
        stmt = select(UserSessionDB).where(
            UserSessionDB.user_id == user_id,
            UserSessionDB.revoked_at_utc.is_(None),
        )
        rows = list(self._session.execute(stmt).scalars().all())
        now = datetime.now(UTC)
        for row in rows:
            row.revoked_at_utc = now
            row.revoked_reason = reason[:128]
        if rows:
            self._session.commit()
        return len(rows)
