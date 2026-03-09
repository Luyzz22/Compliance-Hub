from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import ViolationTable
from app.policy_models import Violation


class ViolationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: ViolationTable) -> Violation:
        return Violation(
            id=row.id,
            tenant_id=row.tenant_id,
            ai_system_id=row.ai_system_id,
            rule_id=row.rule_id,
            message=row.message,
            created_at=row.created_at,
        )

    def get_by_ai_system_and_rule(
        self,
        tenant_id: str,
        ai_system_id: str,
        rule_id: str,
        message: str,
    ) -> Violation | None:
        stmt = select(ViolationTable).where(
            ViolationTable.tenant_id == tenant_id,
            ViolationTable.ai_system_id == ai_system_id,
            ViolationTable.rule_id == rule_id,
            ViolationTable.message == message,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def create_violation(
        self,
        tenant_id: str,
        ai_system_id: str,
        rule_id: str,
        message: str,
    ) -> Violation:
        row = ViolationTable(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            ai_system_id=ai_system_id,
            rule_id=rule_id,
            message=message,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def list_violations_for_tenant(self, tenant_id: str) -> list[Violation]:
        stmt = (
            select(ViolationTable)
            .where(ViolationTable.tenant_id == tenant_id)
            .order_by(ViolationTable.created_at.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]

    def list_violations_for_ai_system(self, tenant_id: str, ai_system_id: str) -> list[Violation]:
        stmt = (
            select(ViolationTable)
            .where(
                ViolationTable.tenant_id == tenant_id,
                ViolationTable.ai_system_id == ai_system_id,
            )
            .order_by(ViolationTable.created_at.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(row) for row in rows]
