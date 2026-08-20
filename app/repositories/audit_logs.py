from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit_integrity import (
    AUDIT_INTEGRITY_V1,
    CURRENT_AUDIT_INTEGRITY_VERSION,
    compute_audit_entry_hash,
)
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
    actor: str = "",
    ip_address: str | None = None,
    user_agent: str | None = None,
    actor_role: str | None = None,
    outcome: str | None = None,
    correlation_id: str | None = None,
    metadata_json: str | None = None,
    integrity_version: str = AUDIT_INTEGRITY_V1,
) -> str:
    """Compatibility wrapper for versioned audit-chain hashing."""
    return compute_audit_entry_hash(
        integrity_version=integrity_version,
        tenant_id=tenant_id,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=created_at,
        actor_role=actor_role,
        outcome=outcome,
        correlation_id=correlation_id,
        metadata_json=metadata_json,
        previous_hash=previous_hash,
    )


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
            integrity_version=row.integrity_version,
            created_at_utc=row.created_at_utc,
            actor_role=row.actor_role,
            outcome=row.outcome,
            correlation_id=row.correlation_id,
            metadata_json=row.metadata_json,
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

    def _lock_tenant_chain(self, tenant_id: str) -> None:
        if self._session.bind is not None and self._session.bind.dialect.name == "postgresql":
            self._session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:tenant_id, 0))"),
                {"tenant_id": tenant_id},
            )

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
        *,
        actor_role: str | None = None,
        outcome: str | None = None,
        correlation_id: str | None = None,
        metadata_json: str | None = None,
    ) -> AuditLog:
        created_at = datetime.now(UTC)
        self._lock_tenant_chain(tenant_id)
        previous_hash = self.get_last_hash(tenant_id)
        integrity_version = CURRENT_AUDIT_INTEGRITY_VERSION
        entry_hash = _compute_entry_hash(
            tenant_id=tenant_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            created_at=created_at,
            previous_hash=previous_hash,
            actor=actor,
            ip_address=ip_address,
            user_agent=user_agent,
            actor_role=actor_role,
            outcome=outcome,
            correlation_id=correlation_id,
            metadata_json=metadata_json,
            integrity_version=integrity_version,
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
            integrity_version=integrity_version,
            created_at_utc=created_at,
            actor_role=actor_role,
            outcome=outcome,
            correlation_id=correlation_id,
            metadata_json=metadata_json,
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
        """Walk all entries and check internal chain consistency (not an external anchor)."""
        stmt = (
            select(AuditLogTable)
            .where(AuditLogTable.tenant_id == tenant_id)
            .order_by(AuditLogTable.id.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        prev_hash: str | None = None
        for row in rows:
            if row.entry_hash is None:
                return False
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
                actor=row.actor,
                ip_address=row.ip_address,
                user_agent=row.user_agent,
                actor_role=row.actor_role,
                outcome=row.outcome,
                correlation_id=row.correlation_id,
                metadata_json=row.metadata_json,
                integrity_version=row.integrity_version,
            )
            if row.entry_hash != expected:
                return False
            prev_hash = row.entry_hash
        return True
