from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_models import AuditLog
from app.models_db import AuditLogTable


def _compute_entry_hash(
    tenant_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: str | None,
    after: str | None,
    created_at: datetime,
    previous_hash: str | None,
) -> str:
    """SHA-256 hash for GoBD-compliant hash chaining."""
    # Normalise to naive UTC so the hash is identical regardless of
    # whether the datetime carries tzinfo (insert) or not (read-back).
    ts = created_at.replace(tzinfo=None).isoformat()
    payload = (
        f"{tenant_id}|{action}|{entity_type}|{entity_id}"
        f"|{before or ''}|{after or ''}"
        f"|{ts}|{previous_hash or ''}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditLogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: AuditLogTable) -> AuditLog:
        return AuditLog(
            id=row.id,
            tenant_id=row.tenant_id,
            actor=row.actor,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            before=row.before,
            after=row.after,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            previous_hash=row.previous_hash,
            entry_hash=row.entry_hash,
            created_at_utc=row.created_at_utc,
        )

    def get_last_hash(self, tenant_id: str) -> str | None:
        """Return the entry_hash of the most recent audit log for the tenant."""
        stmt = (
            select(AuditLogTable.entry_hash)
            .where(AuditLogTable.tenant_id == tenant_id)
            .order_by(AuditLogTable.id.desc())
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def record_event(
        self,
        tenant_id: str,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        before: str | None,
        after: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        created_at = datetime.now(UTC)
        previous_hash = self.get_last_hash(tenant_id)
        entry_hash = _compute_entry_hash(
            tenant_id=tenant_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            created_at=created_at,
            previous_hash=previous_hash,
        )
        row = AuditLogTable(
            tenant_id=tenant_id,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            ip_address=ip_address,
            user_agent=user_agent,
            previous_hash=previous_hash,
            entry_hash=entry_hash,
            created_at_utc=created_at,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def list_for_tenant(self, tenant_id: str, limit: int = 100) -> list[AuditLog]:
        stmt = (
            select(AuditLogTable)
            .where(AuditLogTable.tenant_id == tenant_id)
            .order_by(AuditLogTable.created_at_utc.desc())
            .limit(limit)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]

    def verify_chain_integrity(self, tenant_id: str) -> bool:
        """Walk all entries in chronological order and verify the hash chain."""
        stmt = (
            select(AuditLogTable)
            .where(AuditLogTable.tenant_id == tenant_id)
            .order_by(AuditLogTable.id.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        prev_hash: str | None = None
        for row in rows:
            if row.entry_hash is None:
                prev_hash = None
                continue
            if row.previous_hash != prev_hash:
                return False
            expected = _compute_entry_hash(
                tenant_id=row.tenant_id,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                before=row.before,
                after=row.after,
                created_at=row.created_at_utc,
                previous_hash=row.previous_hash,
            )
            if row.entry_hash != expected:
                return False
            prev_hash = row.entry_hash
        return True
