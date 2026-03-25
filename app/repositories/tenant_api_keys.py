from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import TenantApiKeyDB
from app.security import hash_api_key


class TenantApiKeyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def verify_key(self, *, tenant_id: str, raw_key: str) -> bool:
        digest = hash_api_key(raw_key)
        stmt = select(TenantApiKeyDB).where(
            TenantApiKeyDB.key_hash == digest,
            TenantApiKeyDB.tenant_id == tenant_id,
            TenantApiKeyDB.active.is_(True),
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None

    def list_for_tenant(self, tenant_id: str) -> list[TenantApiKeyDB]:
        stmt = (
            select(TenantApiKeyDB)
            .where(TenantApiKeyDB.tenant_id == tenant_id)
            .order_by(TenantApiKeyDB.created_at_utc.desc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def create_key(self, *, tenant_id: str, name: str) -> tuple[TenantApiKeyDB, str]:
        raw = f"ch_{secrets.token_urlsafe(32)}"
        digest = hash_api_key(raw)
        last4 = raw[-4:] if len(raw) >= 4 else raw
        row = TenantApiKeyDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=name.strip() or "API Key",
            key_hash=digest,
            key_last4=last4,
            active=True,
            created_at_utc=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row, raw

    def revoke(self, *, tenant_id: str, key_id: str) -> TenantApiKeyDB | None:
        stmt = select(TenantApiKeyDB).where(
            TenantApiKeyDB.id == key_id,
            TenantApiKeyDB.tenant_id == tenant_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        row.active = False
        self._session.commit()
        self._session.refresh(row)
        return row
