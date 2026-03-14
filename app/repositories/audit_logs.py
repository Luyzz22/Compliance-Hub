from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit_models import AuditLog
from app.datetime_compat import UTC
from app.models_db import AuditLogTable


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
            created_at_utc=row.created_at_utc,
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
    ) -> AuditLog:
        row = AuditLogTable(
            tenant_id=tenant_id,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            created_at_utc=datetime.now(UTC),
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
