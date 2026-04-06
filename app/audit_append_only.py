"""ORM-level guard: audit_logs rows are append-only (no UPDATE/DELETE in normal flows)."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.models_db import AuditLogTable


@event.listens_for(Session, "before_flush")
def _reject_audit_log_update_or_delete(
    session: Session,
    flush_context: object,
    instances: object,
) -> None:
    for obj in session.deleted:
        if isinstance(obj, AuditLogTable):
            msg = "audit_logs is append-only; DELETE is not permitted"
            raise ValueError(msg)
    for obj in session.dirty:
        if isinstance(obj, AuditLogTable):
            msg = "audit_logs is append-only; UPDATE is not permitted"
            raise ValueError(msg)
