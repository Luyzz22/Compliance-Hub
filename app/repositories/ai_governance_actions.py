from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_governance_action_models import (
    AIGovernanceActionCreate,
    AIGovernanceActionRead,
    AIGovernanceActionUpdate,
    GovernanceActionStatus,
)
from app.models_db import AIGovernanceActionDB


class AIGovernanceActionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_read(row: AIGovernanceActionDB) -> AIGovernanceActionRead:
        return AIGovernanceActionRead(
            id=row.id,
            tenant_id=row.tenant_id,
            related_ai_system_id=row.related_ai_system_id,
            related_requirement=row.related_requirement,
            title=row.title,
            status=GovernanceActionStatus(row.status),
            due_date=row.due_date,
            owner=row.owner,
            created_at_utc=row.created_at_utc,
            updated_at_utc=row.updated_at_utc,
        )

    def create(self, tenant_id: str, body: AIGovernanceActionCreate) -> AIGovernanceActionRead:
        now = datetime.now(UTC)
        row = AIGovernanceActionDB(
            id=str(uuid4()),
            tenant_id=tenant_id,
            related_ai_system_id=body.related_ai_system_id,
            related_requirement=body.related_requirement,
            title=body.title,
            status=body.status.value,
            due_date=body.due_date,
            owner=body.owner,
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_read(row)

    def get(self, tenant_id: str, action_id: str) -> AIGovernanceActionRead | None:
        stmt = select(AIGovernanceActionDB).where(
            AIGovernanceActionDB.id == action_id,
            AIGovernanceActionDB.tenant_id == tenant_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return self._to_read(row) if row else None

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        status: GovernanceActionStatus | None = None,
        limit: int = 100,
    ) -> list[AIGovernanceActionRead]:
        stmt = select(AIGovernanceActionDB).where(AIGovernanceActionDB.tenant_id == tenant_id)
        if status is not None:
            stmt = stmt.where(AIGovernanceActionDB.status == status.value)
        stmt = stmt.order_by(
            AIGovernanceActionDB.due_date.is_(None),
            AIGovernanceActionDB.due_date.asc(),
            AIGovernanceActionDB.created_at_utc.desc(),
        )
        stmt = stmt.limit(limit)
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_read(r) for r in rows]

    def update(
        self,
        tenant_id: str,
        action_id: str,
        body: AIGovernanceActionUpdate,
    ) -> AIGovernanceActionRead | None:
        stmt = select(AIGovernanceActionDB).where(
            AIGovernanceActionDB.id == action_id,
            AIGovernanceActionDB.tenant_id == tenant_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        patch = body.model_dump(exclude_unset=True, mode="json")
        if "related_ai_system_id" in patch:
            row.related_ai_system_id = patch["related_ai_system_id"]
        if "related_requirement" in patch:
            row.related_requirement = patch["related_requirement"]
        if "title" in patch:
            row.title = patch["title"]
        if "status" in patch:
            row.status = patch["status"]
        if "due_date" in patch:
            row.due_date = body.due_date
        if "owner" in patch:
            row.owner = patch["owner"]
        row.updated_at_utc = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(row)
        return self._to_read(row)

    def delete(self, tenant_id: str, action_id: str) -> bool:
        stmt = select(AIGovernanceActionDB).where(
            AIGovernanceActionDB.id == action_id,
            AIGovernanceActionDB.tenant_id == tenant_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True
