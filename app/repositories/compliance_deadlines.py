from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.compliance_calendar_models import (
    ComplianceDeadlineCreate,
    ComplianceDeadlineResponse,
    ComplianceDeadlineUpdate,
    DeadlineCategory,
    DeadlineStatus,
    EscalationLevel,
)
from app.models_db import ComplianceDeadlineTable

_SEED_SOURCE_TYPE = "dach_catalog"
_SYSTEM_SOURCE_TYPE = "system_dach"


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


def _system_deadline_catalog() -> list[tuple[str, ComplianceDeadlineCreate]]:
    """Global system deadlines visible to all tenants (is_system=True, tenant_id=NULL)."""
    return [
        (
            "eu_ai_act_full_20260802",
            ComplianceDeadlineCreate(
                title="EU AI Act – Vollständige Anwendbarkeit",
                category=DeadlineCategory.EU_AI_ACT,
                due_date=date(2026, 8, 2),
                regulation_reference="EU AI Act Art. 113",
                description="Vollständige Anwendbarkeit des EU AI Act.",
            ),
        ),
        (
            "eu_ai_act_banned_20250202",
            ComplianceDeadlineCreate(
                title="EU AI Act – Verbotene Systeme",
                category=DeadlineCategory.EU_AI_ACT,
                due_date=date(2025, 2, 2),
                regulation_reference="EU AI Act Art. 5",
                description="Verbot bestimmter KI-Praktiken tritt in Kraft.",
            ),
        ),
        (
            "eu_ai_act_gpai_20250802",
            ComplianceDeadlineCreate(
                title="EU AI Act – GPAI-Modelle",
                category=DeadlineCategory.EU_AI_ACT,
                due_date=date(2025, 8, 2),
                regulation_reference="EU AI Act Art. 51-56",
                description="Anforderungen an GPAI-Modelle treten in Kraft.",
            ),
        ),
        (
            "nis2_bsig_ongoing",
            ComplianceDeadlineCreate(
                title="NIS2 / BSIG – BSI-Meldepflichten",
                category=DeadlineCategory.NIS2,
                due_date=date(2025, 10, 17),
                regulation_reference="NIS2 Art. 41 / BSIG",
                description="BSI-Meldepflichten (Sektorfristen), laufende Verpflichtung.",
            ),
        ),
        (
            "iso27001_recert_system",
            ComplianceDeadlineCreate(
                title="ISO 27001 / 42001 – Rezertifizierung",
                category=DeadlineCategory.ISO_27001,
                due_date=date(2027, 1, 1),
                regulation_reference="ISO 27001 / ISO 42001",
                description="Rezertifizierung alle 3 Jahre (tenant-konfigurierbar).",
                recurrence_months=36,
            ),
        ),
        (
            "dsgvo_art33_system",
            ComplianceDeadlineCreate(
                title="DSGVO Art. 33 – 72h-Meldefrist",
                category=DeadlineCategory.DSGVO,
                due_date=date(2099, 12, 31),
                regulation_reference="DSGVO Art. 33",
                description="72h-Meldefrist bei Datenschutzverletzungen (per Incident).",
            ),
        ),
        (
            "gobd_147_system",
            ComplianceDeadlineCreate(
                title="GoBD §147 – 10-Jahre-Aufbewahrungsfrist",
                category=DeadlineCategory.GOBD,
                due_date=date(2036, 12, 31),
                regulation_reference="§147 AO / GoBD",
                description="10-Jahre-Aufbewahrungsfrist für steuerrelevante Unterlagen.",
                recurrence_months=120,
            ),
        ),
        (
            "kritis_bsi_kritisv_system",
            ComplianceDeadlineCreate(
                title="KRITIS / BSI-KritisV – Registrierungsfristen",
                category=DeadlineCategory.KRITIS,
                due_date=date(2025, 12, 31),
                regulation_reference="BSI-KritisV",
                description="Sektorspezifische Registrierungsfristen für KRITIS-Betreiber.",
            ),
        ),
    ]


def _catalog_defaults() -> list[tuple[str, ComplianceDeadlineCreate]]:
    return [
        (
            "eu_ai_act_20260802",
            ComplianceDeadlineCreate(
                title="EU AI Act Full Applicability",
                category=DeadlineCategory.EU_AI_ACT,
                due_date=date(2026, 8, 2),
                regulation_reference="Art. 113",
            ),
        ),
        (
            "iso27001_recert_placeholder",
            ComplianceDeadlineCreate(
                title="ISO 27001 Re-Certification",
                category=DeadlineCategory.ISO_27001,
                due_date=date(2027, 1, 1),
                recurrence_months=36,
            ),
        ),
        (
            "iso42001_initial_placeholder",
            ComplianceDeadlineCreate(
                title="ISO 42001 Initial Certification",
                category=DeadlineCategory.ISO_42001,
                due_date=date(2027, 1, 1),
                recurrence_months=36,
            ),
        ),
        (
            "dsgvo_art33_ongoing",
            ComplianceDeadlineCreate(
                title="DSGVO Art. 33 72h Notification Requirement",
                category=DeadlineCategory.DSGVO,
                due_date=date(2099, 12, 31),
                regulation_reference="Art. 33",
                description="Ongoing obligation – 72-hour breach notification window.",
            ),
        ),
        (
            "gobd_147_retention_placeholder",
            ComplianceDeadlineCreate(
                title="GoBD §147 Retention Period End",
                category=DeadlineCategory.GOBD,
                due_date=date(2036, 12, 31),
                regulation_reference="§147 AO",
                recurrence_months=120,
            ),
        ),
        (
            "nis2_nat_impl_20251017",
            ComplianceDeadlineCreate(
                title="NIS2 National Implementation Deadline",
                category=DeadlineCategory.NIS2,
                due_date=date(2025, 10, 17),
                regulation_reference="Art. 41",
            ),
        ),
    ]


class ComplianceDeadlineRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: ComplianceDeadlineTable) -> ComplianceDeadlineResponse:
        due = date.fromisoformat(row.due_date)
        level, remaining = _compute_escalation(due)
        raw_status = getattr(row, "status", None) or "open"
        valid_values = {v.value for v in DeadlineStatus}
        status = DeadlineStatus(raw_status) if raw_status in valid_values else DeadlineStatus.OPEN
        if status != DeadlineStatus.COMPLETED and remaining < 0:
            status = DeadlineStatus.OVERDUE
        return ComplianceDeadlineResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            title=row.title,
            description=row.description,
            category=DeadlineCategory(row.category),
            due_date=due,
            status=status,
            owner=row.owner,
            regulation_reference=row.regulation_reference,
            recurrence_months=row.recurrence_months,
            is_system=getattr(row, "is_system", False) or False,
            source_type=row.source_type,
            source_id=row.source_id,
            escalation_level=level,
            days_remaining=remaining,
            created_at_utc=row.created_at_utc,
        )

    def _get_by_source(
        self, tenant_id: str | None, source_type: str, source_id: str
    ) -> ComplianceDeadlineTable | None:
        if tenant_id is None:
            stmt = select(ComplianceDeadlineTable).where(
                ComplianceDeadlineTable.tenant_id.is_(None),
                ComplianceDeadlineTable.source_type == source_type,
                ComplianceDeadlineTable.source_id == source_id,
            )
        else:
            stmt = select(ComplianceDeadlineTable).where(
                ComplianceDeadlineTable.tenant_id == tenant_id,
                ComplianceDeadlineTable.source_type == source_type,
                ComplianceDeadlineTable.source_id == source_id,
            )
        return self._session.execute(stmt).scalar_one_or_none()

    def create(self, tenant_id: str, data: ComplianceDeadlineCreate) -> ComplianceDeadlineResponse:
        row = ComplianceDeadlineTable(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            title=data.title,
            description=data.description,
            category=data.category.value,
            due_date=data.due_date.isoformat(),
            status=data.status.value if data.status else DeadlineStatus.OPEN.value,
            owner=data.owner,
            regulation_reference=data.regulation_reference,
            recurrence_months=data.recurrence_months,
            is_system=False,
            source_type=None,
            source_id=None,
            created_at_utc=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def get(self, tenant_id: str, deadline_id: str) -> ComplianceDeadlineResponse | None:
        stmt = select(ComplianceDeadlineTable).where(
            or_(
                ComplianceDeadlineTable.tenant_id == tenant_id,
                ComplianceDeadlineTable.is_system == True,  # noqa: E712
            ),
            ComplianceDeadlineTable.id == deadline_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def list_for_tenant(self, tenant_id: str, limit: int = 100) -> list[ComplianceDeadlineResponse]:
        stmt = (
            select(ComplianceDeadlineTable)
            .where(
                or_(
                    ComplianceDeadlineTable.tenant_id == tenant_id,
                    ComplianceDeadlineTable.is_system == True,  # noqa: E712
                )
            )
            .order_by(ComplianceDeadlineTable.due_date)
            .limit(limit)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]

    def list_upcoming(self, tenant_id: str, days: int = 90) -> list[ComplianceDeadlineResponse]:
        """Return deadlines within the next *days* days (plus system deadlines)."""
        from datetime import timedelta

        cutoff = date.today()
        cutoff_end = (cutoff + timedelta(days=days)).isoformat()
        stmt = (
            select(ComplianceDeadlineTable)
            .where(
                or_(
                    ComplianceDeadlineTable.tenant_id == tenant_id,
                    ComplianceDeadlineTable.is_system == True,  # noqa: E712
                ),
                ComplianceDeadlineTable.due_date >= cutoff.isoformat(),
                ComplianceDeadlineTable.due_date <= cutoff_end,
            )
            .order_by(ComplianceDeadlineTable.due_date)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]

    def is_system_deadline(self, deadline_id: str) -> bool:
        """Check if a deadline is a system deadline (immutable)."""
        stmt = select(ComplianceDeadlineTable).where(
            ComplianceDeadlineTable.id == deadline_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return False
        return getattr(row, "is_system", False) or False

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
            elif field == "status" and value is not None:
                setattr(row, field, value.value if hasattr(value, "value") else value)
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

    def seed_system_deadlines(self) -> list[ComplianceDeadlineResponse]:
        """Idempotent: create global system deadlines (is_system=True, tenant_id=NULL)."""
        out: list[ComplianceDeadlineResponse] = []
        for source_id, payload in _system_deadline_catalog():
            existing = self._get_by_source(None, _SYSTEM_SOURCE_TYPE, source_id)
            if existing is not None:
                out.append(self._to_domain(existing))
                continue
            row = ComplianceDeadlineTable(
                id=str(uuid.uuid4()),
                tenant_id=None,
                title=payload.title,
                description=payload.description,
                category=payload.category.value,
                due_date=payload.due_date.isoformat(),
                status=DeadlineStatus.OPEN.value,
                owner=None,
                regulation_reference=payload.regulation_reference,
                recurrence_months=payload.recurrence_months,
                is_system=True,
                source_type=_SYSTEM_SOURCE_TYPE,
                source_id=source_id,
                created_at_utc=datetime.now(UTC),
            )
            self._session.add(row)
            self._session.commit()
            self._session.refresh(row)
            out.append(self._to_domain(row))
        return out

    def seed_dach_defaults(self, tenant_id: str) -> list[ComplianceDeadlineResponse]:
        """Idempotent: one row per catalog *source_id* per tenant (unique partial index)."""
        out: list[ComplianceDeadlineResponse] = []
        for source_id, payload in _catalog_defaults():
            existing = self._get_by_source(tenant_id, _SEED_SOURCE_TYPE, source_id)
            if existing is not None:
                out.append(self._to_domain(existing))
                continue
            row = ComplianceDeadlineTable(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                title=payload.title,
                description=payload.description,
                category=payload.category.value,
                due_date=payload.due_date.isoformat(),
                status=DeadlineStatus.OPEN.value,
                owner=payload.owner,
                regulation_reference=payload.regulation_reference,
                recurrence_months=payload.recurrence_months,
                is_system=False,
                source_type=_SEED_SOURCE_TYPE,
                source_id=source_id,
                created_at_utc=datetime.now(UTC),
            )
            self._session.add(row)
            self._session.commit()
            self._session.refresh(row)
            out.append(self._to_domain(row))
        return out
