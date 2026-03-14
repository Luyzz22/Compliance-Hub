from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.audit_models import AuditEvent
from app.datetime_compat import UTC
from app.models_db import Base


class AuditEventTable(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: AuditEventTable) -> AuditEvent:
        return AuditEvent(
            id=row.id,
            tenant_id=row.tenant_id,
            timestamp=row.timestamp,
            actor_type=row.actor_type,
            actor_id=row.actor_id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            metadata=row.metadata_json,
        )

    def log_event(
        self,
        tenant_id: str,
        actor_type: str,
        entity_type: str,
        entity_id: str,
        action: str,
        actor_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        row = AuditEventTable(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            timestamp=datetime.now(UTC),
            actor_type=actor_type,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            metadata_json=metadata,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def list_events_for_tenant(
        self,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        stmt = (
            select(AuditEventTable)
            .where(AuditEventTable.tenant_id == tenant_id)
            .order_by(AuditEventTable.timestamp.desc(), AuditEventTable.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]

    def list_events_for_entity(
        self,
        tenant_id: str,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEvent]:
        stmt = (
            select(AuditEventTable)
            .where(
                AuditEventTable.tenant_id == tenant_id,
                AuditEventTable.entity_type == entity_type,
                AuditEventTable.entity_id == entity_id,
            )
            .order_by(AuditEventTable.timestamp.desc(), AuditEventTable.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]
