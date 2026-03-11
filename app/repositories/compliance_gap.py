from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compliance_gap_models import (
    ComplianceStatus,
    ComplianceStatusEntry,
    ComplianceStatusUpdate,
    REQUIREMENTS,
    REQUIREMENTS_BY_ID,
)
from app.models_db import ComplianceStatusTable


class ComplianceGapRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: ComplianceStatusTable) -> ComplianceStatusEntry:
        return ComplianceStatusEntry(
            ai_system_id=row.ai_system_id,
            requirement_id=row.requirement_id,
            status=row.status,
            evidence_notes=row.evidence_notes,
            last_updated=row.last_updated,
            updated_by=row.updated_by,
        )

    def list_for_system(self, tenant_id: str, ai_system_id: str) -> list[ComplianceStatusEntry]:
        stmt = (
            select(ComplianceStatusTable)
            .where(
                ComplianceStatusTable.tenant_id == tenant_id,
                ComplianceStatusTable.ai_system_id == ai_system_id,
            )
            .order_by(ComplianceStatusTable.requirement_id)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]

    def ensure_requirements_exist(
        self, tenant_id: str, ai_system_id: str, risk_level: str
    ) -> list[ComplianceStatusEntry]:
        """Ensure all applicable requirements are tracked for this system."""
        existing_stmt = (
            select(ComplianceStatusTable.requirement_id)
            .where(
                ComplianceStatusTable.tenant_id == tenant_id,
                ComplianceStatusTable.ai_system_id == ai_system_id,
            )
        )
        existing_ids = set(self._session.execute(existing_stmt).scalars().all())

        for req in REQUIREMENTS:
            if risk_level in req.applies_to and req.id not in existing_ids:
                row = ComplianceStatusTable(
                    tenant_id=tenant_id,
                    ai_system_id=ai_system_id,
                    requirement_id=req.id,
                    status=ComplianceStatus.not_started,
                    evidence_notes=None,
                    last_updated=datetime.now(UTC),
                    updated_by="system",
                )
                self._session.add(row)
        self._session.commit()
        return self.list_for_system(tenant_id, ai_system_id)

    def update_status(
        self,
        tenant_id: str,
        ai_system_id: str,
        requirement_id: str,
        update: ComplianceStatusUpdate,
        user_id: str,
    ) -> ComplianceStatusEntry | None:
        stmt = select(ComplianceStatusTable).where(
            ComplianceStatusTable.tenant_id == tenant_id,
            ComplianceStatusTable.ai_system_id == ai_system_id,
            ComplianceStatusTable.requirement_id == requirement_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        row.status = update.status
        if update.evidence_notes is not None:
            row.evidence_notes = update.evidence_notes
        row.last_updated = datetime.now(UTC)
        row.updated_by = user_id
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def list_all_for_tenant(self, tenant_id: str) -> list[ComplianceStatusEntry]:
        stmt = (
            select(ComplianceStatusTable)
            .where(ComplianceStatusTable.tenant_id == tenant_id)
            .order_by(ComplianceStatusTable.ai_system_id, ComplianceStatusTable.requirement_id)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]
