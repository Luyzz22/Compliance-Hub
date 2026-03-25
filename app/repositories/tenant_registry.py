from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import TenantDB


class TenantRegistryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, tenant_id: str) -> TenantDB | None:
        stmt = select(TenantDB).where(TenantDB.id == tenant_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def create(
        self,
        *,
        tenant_id: str,
        display_name: str,
        industry: str,
        country: str,
        nis2_scope: str,
        ai_act_scope: str,
        is_demo: bool = False,
        demo_playground: bool = False,
    ) -> TenantDB:
        row = TenantDB(
            id=tenant_id,
            display_name=display_name,
            industry=industry,
            country=country,
            nis2_scope=nis2_scope,
            ai_act_scope=ai_act_scope,
            is_demo=is_demo,
            demo_playground=demo_playground,
            created_at_utc=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row
