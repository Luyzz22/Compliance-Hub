from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_system_models import AISystem, AISystemCreate, AISystemStatus
from app.models_db import AISystemTable


class AISystemRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: AISystemTable) -> AISystem:
        return AISystem(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            business_unit=row.business_unit,
            risk_level=row.risk_level,
            ai_act_category=row.ai_act_category,
            gdpr_dpia_required=row.gdpr_dpia_required,
            owner_email=row.owner_email,
            status=row.status,
            created_at_utc=row.created_at_utc,
            updated_at_utc=row.updated_at_utc,
        )

    def get_by_id(self, tenant_id: str, aisystem_id: str) -> AISystem | None:
        stmt = select(AISystemTable).where(
            AISystemTable.tenant_id == tenant_id,
            AISystemTable.id == aisystem_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def list_for_tenant(self, tenant_id: str) -> list[AISystem]:
        stmt = (
            select(AISystemTable)
            .where(AISystemTable.tenant_id == tenant_id)
            .order_by(AISystemTable.created_at_utc.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]

    def create(self, tenant_id: str, payload: AISystemCreate) -> AISystem:
        now = datetime.now(timezone.utc)
        row = AISystemTable(
            id=payload.id,
            tenant_id=tenant_id,
            name=payload.name,
            description=payload.description,
            business_unit=payload.business_unit,
            risk_level=payload.risk_level,
            ai_act_category=payload.ai_act_category,
            gdpr_dpia_required=payload.gdpr_dpia_required,
            owner_email=str(payload.owner_email),
            status=AISystemStatus.draft,
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def update_status(self, tenant_id: str, aisystem_id: str, new_status: AISystemStatus) -> AISystem:
        stmt = select(AISystemTable).where(
            AISystemTable.tenant_id == tenant_id,
            AISystemTable.id == aisystem_id,
        )
        row = self._session.execute(stmt).scalar_one()
        row.status = new_status
        row.updated_at_utc = datetime.now(timezone.utc)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)
