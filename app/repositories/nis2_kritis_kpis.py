from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models_db import AISystemTable, Nis2KritisKpiDB
from app.nis2_kritis_models import Nis2KritisKpi, Nis2KritisKpiType


class Nis2KritisKpiRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: Nis2KritisKpiDB) -> Nis2KritisKpi:
        return Nis2KritisKpi(
            id=row.id,
            ai_system_id=row.ai_system_id,
            kpi_type=Nis2KritisKpiType(row.kpi_type),
            value_percent=row.value_percent,
            evidence_ref=row.evidence_ref,
            last_reviewed_at=row.last_reviewed_at,
        )

    def list_for_ai_system(self, tenant_id: str, ai_system_id: str) -> list[Nis2KritisKpi]:
        stmt = (
            select(Nis2KritisKpiDB)
            .where(
                Nis2KritisKpiDB.tenant_id == tenant_id,
                Nis2KritisKpiDB.ai_system_id == ai_system_id,
            )
            .order_by(Nis2KritisKpiDB.kpi_type)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]

    def upsert(
        self,
        tenant_id: str,
        ai_system_id: str,
        kpi_type: Nis2KritisKpiType,
        value_percent: int,
        evidence_ref: str | None,
        last_reviewed_at: datetime | None,
    ) -> Nis2KritisKpi:
        stmt = select(Nis2KritisKpiDB).where(
            Nis2KritisKpiDB.tenant_id == tenant_id,
            Nis2KritisKpiDB.ai_system_id == ai_system_id,
            Nis2KritisKpiDB.kpi_type == kpi_type.value,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            row = Nis2KritisKpiDB(
                id=str(uuid4()),
                tenant_id=tenant_id,
                ai_system_id=ai_system_id,
                kpi_type=kpi_type.value,
                value_percent=value_percent,
                evidence_ref=evidence_ref,
                last_reviewed_at=last_reviewed_at,
            )
            self._session.add(row)
        else:
            row.value_percent = value_percent
            row.evidence_ref = evidence_ref
            row.last_reviewed_at = last_reviewed_at

        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def aggregate_for_tenant(self, tenant_id: str) -> tuple[float | None, float]:
        """Mittelwert aller KPI-Werte; Anteil Systeme mit allen drei KPI-Typen."""
        mean_stmt = select(func.avg(Nis2KritisKpiDB.value_percent)).where(
            Nis2KritisKpiDB.tenant_id == tenant_id,
        )
        mean_val = self._session.execute(mean_stmt).scalar_one()
        mean_percent: float | None = float(mean_val) if mean_val is not None else None

        systems_stmt = select(AISystemTable.id).where(AISystemTable.tenant_id == tenant_id)
        system_ids = list(self._session.execute(systems_stmt).scalars().all())
        total = len(system_ids)
        if total == 0:
            return mean_percent, 0.0

        count_stmt = (
            select(Nis2KritisKpiDB.ai_system_id, func.count(Nis2KritisKpiDB.id))
            .where(
                Nis2KritisKpiDB.tenant_id == tenant_id,
                Nis2KritisKpiDB.kpi_type.in_([e.value for e in Nis2KritisKpiType]),
            )
            .group_by(Nis2KritisKpiDB.ai_system_id)
        )
        counts: dict[str, int] = defaultdict(int)
        for sid, cnt in self._session.execute(count_stmt).all():
            counts[sid] = int(cnt)

        full = sum(1 for sid in system_ids if counts.get(sid, 0) >= len(Nis2KritisKpiType))
        ratio = full / total
        return mean_percent, ratio
