from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compliance_calendar_models import (
    ComplianceDeadlineCreate,
    ComplianceDeadlineResponse,
    ComplianceDeadlineUpdate,
    DeadlineCategory,
    EscalationLevel,
)
from app.models_db import ComplianceDeadlineTable


def _compute_escalation(due_date: date) -> tuple[EscalationLevel, int]:
    """Return (escalation_level, days_remaining) based on how close the due date is."""
    days_remaining = (due_date - date.today()).days
    if days_remaining < 0:
        return EscalationLevel.OVERDUE, days_remaining
    if days_remaining <= 7:
        return EscalationLevel.CRITICAL, days_remaining
    if days_remaining <= 14:
        return EscalationLevel.WARNING, days_remaining
    if days_remaining <= 30:
        return EscalationLevel.INFO, days_remaining
    return EscalationLevel.NONE, days_remaining


class ComplianceDeadlineRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: ComplianceDeadlineTable) -> ComplianceDeadlineResponse:
        due = date.fromisoformat(row.due_date)
        level, remaining = _compute_escalation(due)
        return ComplianceDeadlineResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            title=row.title,
            description=row.description,
            category=DeadlineCategory(row.category),
            due_date=due,
            owner=row.owner,
            regulation_reference=row.regulation_reference,
            recurrence_months=row.recurrence_months,
            escalation_level=level,
            days_remaining=remaining,
            created_at_utc=row.created_at_utc,
        )

    def create(self, tenant_id: str, data: ComplianceDeadlineCreate) -> ComplianceDeadlineResponse:
        row = ComplianceDeadlineTable(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            title=data.title,
            description=data.description,
            category=data.category.value,
            due_date=data.due_date.isoformat(),
            owner=data.owner,
            regulation_reference=data.regulation_reference,
            recurrence_months=data.recurrence_months,
            created_at_utc=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def get(self, tenant_id: str, deadline_id: str) -> ComplianceDeadlineResponse | None:
        stmt = select(ComplianceDeadlineTable).where(
            ComplianceDeadlineTable.tenant_id == tenant_id,
            ComplianceDeadlineTable.id == deadline_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def list_for_tenant(self, tenant_id: str, limit: int = 100) -> list[ComplianceDeadlineResponse]:
        stmt = (
            select(ComplianceDeadlineTable)
            .where(ComplianceDeadlineTable.tenant_id == tenant_id)
            .order_by(ComplianceDeadlineTable.due_date)
            .limit(limit)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]

    def update(
        self, tenant_id: str, deadline_id: str, data: ComplianceDeadlineUpdate
    ) -> ComplianceDeadlineResponse | None:
        stmt = select(ComplianceDeadlineTable).where(
            ComplianceDeadlineTable.tenant_id == tenant_id,
            ComplianceDeadlineTable.id == deadline_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            if field == "due_date" and value is not None:
                setattr(row, field, value.isoformat())
            else:
                setattr(row, field, value)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def delete(self, tenant_id: str, deadline_id: str) -> bool:
        stmt = select(ComplianceDeadlineTable).where(
            ComplianceDeadlineTable.tenant_id == tenant_id,
            ComplianceDeadlineTable.id == deadline_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return False
        self._session.delete(row)
        self._session.commit()
        return True

    def seed_dach_defaults(self, tenant_id: str) -> list[ComplianceDeadlineResponse]:
        """Idempotent: skips defaults whose title already exists for this tenant."""
        existing_stmt = select(ComplianceDeadlineTable.title).where(
            ComplianceDeadlineTable.tenant_id == tenant_id,
        )
        existing_titles = set(self._session.execute(existing_stmt).scalars().all())

        defaults = [
            ComplianceDeadlineCreate(
                title="EU AI Act Full Applicability",
                category=DeadlineCategory.EU_AI_ACT,
                due_date=date(2026, 8, 2),
                regulation_reference="Art. 113",
            ),
            ComplianceDeadlineCreate(
                title="ISO 27001 Re-Certification",
                category=DeadlineCategory.ISO_27001,
                due_date=date(2027, 1, 1),
                recurrence_months=36,
            ),
            ComplianceDeadlineCreate(
                title="ISO 42001 Initial Certification",
                category=DeadlineCategory.ISO_42001,
                due_date=date(2027, 1, 1),
                recurrence_months=36,
            ),
            ComplianceDeadlineCreate(
                title="DSGVO Art. 33 72h Notification Requirement",
                category=DeadlineCategory.DSGVO,
                due_date=date(2099, 12, 31),
                regulation_reference="Art. 33",
                description="Ongoing obligation – 72-hour breach notification window.",
            ),
            ComplianceDeadlineCreate(
                title="GoBD §147 Retention Period End",
                category=DeadlineCategory.GOBD,
                due_date=date(2036, 12, 31),
                regulation_reference="§147 AO",
                recurrence_months=120,
            ),
            ComplianceDeadlineCreate(
                title="NIS2 National Implementation Deadline",
                category=DeadlineCategory.NIS2,
                due_date=date(2025, 10, 17),
                regulation_reference="Art. 41",
            ),
        ]
        result: list[ComplianceDeadlineResponse] = []
        for d in defaults:
            if d.title not in existing_titles:
                result.append(self.create(tenant_id, d))
        return result
