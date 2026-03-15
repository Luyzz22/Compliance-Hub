"""Incident-Repository für NIS2 Art. 21/23 und ISO 42001 Incident Management.

Mandantenfähig: Alle Queries filtern strikt nach tenant_id (RLS-konform).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.incident_models import IncidentSeverity, IncidentStatus
from app.models_db import IncidentTable


class IncidentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_tenant_last_12_months(self, tenant_id: str) -> list[IncidentTable]:
        """Alle Incidents des Tenants der letzten 12 Monate (für Aggregationen)."""
        since = datetime.now(UTC) - timedelta(days=365)
        stmt = (
            select(IncidentTable)
            .where(
                IncidentTable.tenant_id == tenant_id,
                IncidentTable.created_at_utc >= since,
            )
            .order_by(IncidentTable.created_at_utc.desc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return list(rows)

    def count_open_for_tenant(self, tenant_id: str) -> int:
        """Anzahl offene Incidents (status open) des Tenants."""
        stmt = select(func.count(IncidentTable.id)).where(
            IncidentTable.tenant_id == tenant_id,
            IncidentTable.status == IncidentStatus.open.value,
        )
        return self._session.execute(stmt).scalar_one() or 0

    def aggregate_overview(
        self,
        tenant_id: str,
    ) -> tuple[int, int, int, float | None, float | None, list[tuple[str, int]]]:
        """Liefert (total_12m, open, major_12m, mtta_h, mttr_h, by_severity_list)."""
        since = datetime.now(UTC) - timedelta(days=365)
        # Total last 12 months
        stmt_total = select(func.count(IncidentTable.id)).where(
            IncidentTable.tenant_id == tenant_id,
            IncidentTable.created_at_utc >= since,
        )
        total = self._session.execute(stmt_total).scalar_one() or 0
        open_count = self.count_open_for_tenant(tenant_id)
        # Major (high severity) last 12 months
        stmt_major = select(func.count(IncidentTable.id)).where(
            IncidentTable.tenant_id == tenant_id,
            IncidentTable.created_at_utc >= since,
            IncidentTable.severity == IncidentSeverity.high.value,
        )
        major = self._session.execute(stmt_major).scalar_one() or 0
        # By severity (last 12 months)
        stmt_sev = (
            select(IncidentTable.severity, func.count(IncidentTable.id))
            .where(
                IncidentTable.tenant_id == tenant_id,
                IncidentTable.created_at_utc >= since,
            )
            .group_by(IncidentTable.severity)
        )
        by_severity_rows = self._session.execute(stmt_sev).all()
        by_severity = [(sev, cnt) for sev, cnt in by_severity_rows]
        # MTTA / MTTR: aus acknowledged_at_utc - created_at_utc bzw. resolved - created
        rows = self.list_for_tenant_last_12_months(tenant_id)
        mtta_hours: list[float] = []
        mttr_hours: list[float] = []
        for row in rows:
            if row.acknowledged_at_utc and row.created_at_utc:
                delta = row.acknowledged_at_utc - row.created_at_utc
                mtta_hours.append(delta.total_seconds() / 3600.0)
            if row.resolved_at_utc and row.created_at_utc:
                delta = row.resolved_at_utc - row.created_at_utc
                mttr_hours.append(delta.total_seconds() / 3600.0)
        mtta = sum(mtta_hours) / len(mtta_hours) if mtta_hours else None
        mttr = sum(mttr_hours) / len(mttr_hours) if mttr_hours else None
        return (total, open_count, major, mtta, mttr, by_severity)

    def aggregate_by_system(
        self,
        tenant_id: str,
    ) -> list[tuple[str, int, datetime | None]]:
        """(ai_system_id, incident_count, last_incident_at) pro System, letzte 12 Monate."""
        since = datetime.now(UTC) - timedelta(days=365)
        stmt = (
            select(
                IncidentTable.ai_system_id,
                func.count(IncidentTable.id).label("cnt"),
                func.max(IncidentTable.created_at_utc).label("last_at"),
            )
            .where(
                IncidentTable.tenant_id == tenant_id,
                IncidentTable.created_at_utc >= since,
            )
            .group_by(IncidentTable.ai_system_id)
        )
        rows = self._session.execute(stmt).all()
        return [(r[0], r[1], r[2]) for r in rows]
