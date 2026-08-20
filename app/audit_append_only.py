"""ORM-level guard: audit_logs rows are append-only (no UPDATE/DELETE in normal flows)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from app.audit_integrity import CURRENT_AUDIT_INTEGRITY_VERSION, compute_audit_entry_hash
from app.models_db import AuditLogTable


@event.listens_for(Session, "before_flush")
def _reject_audit_log_update_or_delete(
    session: Session,
    flush_context: object,
    instances: object,
) -> None:
    chain_heads: dict[str, str | None] = {}
    locked_tenants: set[str] = set()
    for obj in session.new:
        if not isinstance(obj, AuditLogTable):
            continue
        tenant_id = obj.tenant_id
        if tenant_id not in locked_tenants:
            if session.bind is not None and session.bind.dialect.name == "postgresql":
                session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:tenant_id, 0))"),
                    {"tenant_id": tenant_id},
                )
            locked_tenants.add(tenant_id)
        if tenant_id not in chain_heads:
            chain_heads[tenant_id] = session.execute(
                select(AuditLogTable.entry_hash)
                .where(AuditLogTable.tenant_id == tenant_id)
                .order_by(AuditLogTable.id.desc())
                .limit(1),
            ).scalar_one_or_none()
        if obj.entry_hash is None:
            if obj.created_at_utc is None:
                obj.created_at_utc = datetime.now(UTC)
            obj.integrity_version = CURRENT_AUDIT_INTEGRITY_VERSION
            obj.previous_hash = chain_heads[tenant_id]
            obj.entry_hash = compute_audit_entry_hash(
                integrity_version=obj.integrity_version,
                tenant_id=obj.tenant_id,
                actor=obj.actor,
                action=obj.action,
                entity_type=obj.entity_type,
                entity_id=obj.entity_id,
                before=obj.before,
                after=obj.after,
                ip_address=obj.ip_address,
                user_agent=obj.user_agent,
                created_at=obj.created_at_utc,
                actor_role=obj.actor_role,
                outcome=obj.outcome,
                correlation_id=obj.correlation_id,
                metadata_json=obj.metadata_json,
                previous_hash=obj.previous_hash,
            )
        chain_heads[tenant_id] = obj.entry_hash

    for obj in session.deleted:
        if isinstance(obj, AuditLogTable):
            msg = "audit_logs is append-only; DELETE is not permitted"
            raise ValueError(msg)
    for obj in session.dirty:
        if isinstance(obj, AuditLogTable):
            msg = "audit_logs is append-only; UPDATE is not permitted"
            raise ValueError(msg)
