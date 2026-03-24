from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from uuid import uuid4

from sqlalchemy import func, or_, select
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

    def mean_percent_by_kpi_type(self, tenant_id: str) -> dict[Nis2KritisKpiType, float | None]:
        """Arithmetisches Mittel je KPI-Typ (None, wenn keine Werte)."""
        out: dict[Nis2KritisKpiType, float | None] = {}
        for kt in Nis2KritisKpiType:
            stmt = select(func.avg(Nis2KritisKpiDB.value_percent)).where(
                Nis2KritisKpiDB.tenant_id == tenant_id,
                Nis2KritisKpiDB.kpi_type == kt.value,
            )
            raw = self._session.execute(stmt).scalar_one()
            out[kt] = float(raw) if raw is not None else None
        return out

    def count_focus_systems_ot_it_below(
        self,
        tenant_id: str,
        *,
        threshold_percent: int,
    ) -> int:
        """
        Zählt KI-Systeme mit OT/IT-KPI unter Schwellwert und Fokusprofil
        (High-Risk, High-Risk-Kategorie oder hohe KRITIS-ähnliche Criticality).
        """
        stmt = (
            select(func.count())
            .select_from(Nis2KritisKpiDB)
            .join(AISystemTable, AISystemTable.id == Nis2KritisKpiDB.ai_system_id)
            .where(
                Nis2KritisKpiDB.tenant_id == tenant_id,
                AISystemTable.tenant_id == tenant_id,
                Nis2KritisKpiDB.kpi_type == Nis2KritisKpiType.OT_IT_SEGREGATION.value,
                Nis2KritisKpiDB.value_percent < threshold_percent,
                or_(
                    AISystemTable.risk_level == "high",
                    AISystemTable.ai_act_category == "high_risk",
                    AISystemTable.criticality.in_(("high", "very_high")),
                ),
            )
        )
        return int(self._session.execute(stmt).scalar_one() or 0)

    def list_kpis_with_system_for_tenant(
        self,
        tenant_id: str,
    ) -> list[tuple[Nis2KritisKpi, str, str]]:
        """Alle KPI-Zeilen mit Systemname und Geschäftsbereich (Join)."""
        stmt = (
            select(
                Nis2KritisKpiDB,
                AISystemTable.name,
                AISystemTable.business_unit,
            )
            .join(AISystemTable, AISystemTable.id == Nis2KritisKpiDB.ai_system_id)
            .where(
                Nis2KritisKpiDB.tenant_id == tenant_id,
                AISystemTable.tenant_id == tenant_id,
            )
            .order_by(Nis2KritisKpiDB.kpi_type, Nis2KritisKpiDB.value_percent)
        )
        rows = self._session.execute(stmt).all()
        return [(self._to_domain(r[0]), str(r[1]), str(r[2])) for r in rows]

    def list_system_ids_lowest_kpi(
        self,
        tenant_id: str,
        kpi_type: Nis2KritisKpiType,
        *,
        limit: int = 3,
    ) -> list[str]:
        """KI-System-IDs mit niedrigstem KPI-Wert (für Alert-Kontext, Top-N)."""
        stmt = (
            select(Nis2KritisKpiDB.ai_system_id)
            .where(
                Nis2KritisKpiDB.tenant_id == tenant_id,
                Nis2KritisKpiDB.kpi_type == kpi_type.value,
            )
            .order_by(Nis2KritisKpiDB.value_percent.asc(), Nis2KritisKpiDB.ai_system_id.asc())
            .limit(limit)
        )
        return [str(x) for x in self._session.execute(stmt).scalars().all()]

    def list_focus_system_ids_ot_it_below(
        self,
        tenant_id: str,
        *,
        threshold_percent: int,
        limit: int = 3,
    ) -> list[str]:
        """Fokus-Systeme mit OT/IT-KPI unter Schwellwert, niedrigste zuerst."""
        stmt = (
            select(Nis2KritisKpiDB.ai_system_id)
            .select_from(Nis2KritisKpiDB)
            .join(AISystemTable, AISystemTable.id == Nis2KritisKpiDB.ai_system_id)
            .where(
                Nis2KritisKpiDB.tenant_id == tenant_id,
                AISystemTable.tenant_id == tenant_id,
                Nis2KritisKpiDB.kpi_type == Nis2KritisKpiType.OT_IT_SEGREGATION.value,
                Nis2KritisKpiDB.value_percent < threshold_percent,
                or_(
                    AISystemTable.risk_level == "high",
                    AISystemTable.ai_act_category == "high_risk",
                    AISystemTable.criticality.in_(("high", "very_high")),
                ),
            )
            .order_by(Nis2KritisKpiDB.value_percent.asc(), Nis2KritisKpiDB.ai_system_id.asc())
            .limit(limit)
        )
        return [str(x) for x in self._session.execute(stmt).scalars().all()]
