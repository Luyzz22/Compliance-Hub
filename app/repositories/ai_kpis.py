"""Repository: AI-KPI-Definitionen und System-Zeitreihen (tenant-isoliert)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import AiKpiDefinitionDB, AiSystemKpiValueDB, AISystemTable


class AiKpiRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_definitions(self) -> list[AiKpiDefinitionDB]:
        stmt = select(AiKpiDefinitionDB).order_by(AiKpiDefinitionDB.key)
        return list(self._session.execute(stmt).scalars().all())

    def get_definition(self, definition_id: str) -> AiKpiDefinitionDB | None:
        return self._session.get(AiKpiDefinitionDB, definition_id)

    def list_values_for_system(
        self,
        tenant_id: str,
        ai_system_id: str,
    ) -> list[AiSystemKpiValueDB]:
        stmt = (
            select(AiSystemKpiValueDB)
            .where(
                AiSystemKpiValueDB.tenant_id == tenant_id,
                AiSystemKpiValueDB.ai_system_id == ai_system_id,
            )
            .order_by(AiSystemKpiValueDB.period_start.desc())
        )
        return list(self._session.execute(stmt).scalars().all())

    def upsert_value(
        self,
        *,
        tenant_id: str,
        ai_system_id: str,
        kpi_definition_id: str,
        period_start: datetime,
        period_end: datetime,
        value: float,
        source: str,
        comment: str | None,
        new_id: str,
    ) -> AiSystemKpiValueDB:
        stmt = select(AiSystemKpiValueDB).where(
            AiSystemKpiValueDB.tenant_id == tenant_id,
            AiSystemKpiValueDB.ai_system_id == ai_system_id,
            AiSystemKpiValueDB.kpi_definition_id == kpi_definition_id,
            AiSystemKpiValueDB.period_start == period_start,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            row = AiSystemKpiValueDB(
                id=new_id,
                tenant_id=tenant_id,
                ai_system_id=ai_system_id,
                kpi_definition_id=kpi_definition_id,
                period_start=period_start,
                period_end=period_end,
                value=value,
                source=source,
                comment=comment,
            )
            self._session.add(row)
        else:
            row.period_end = period_end
            row.value = value
            row.source = source
            row.comment = comment
        self._session.commit()
        self._session.refresh(row)
        return row

    def list_high_risk_system_ids(
        self,
        tenant_id: str,
        *,
        min_risk_levels: frozenset[str] | None = None,
        criticalities: frozenset[str] | None = None,
    ) -> list[tuple[str, str, str, str]]:
        """(id, name, risk_level, criticality) für gefilterte Systeme."""
        levels = min_risk_levels or frozenset({"high", "unacceptable"})
        stmt = select(
            AISystemTable.id,
            AISystemTable.name,
            AISystemTable.risk_level,
            AISystemTable.criticality,
        ).where(AISystemTable.tenant_id == tenant_id)
        rows = self._session.execute(stmt).all()
        out: list[tuple[str, str, str, str]] = []
        for rid, name, rl, crit in rows:
            rls = str(rl).lower()
            if rls not in levels:
                continue
            if criticalities is not None:
                c = str(crit).lower()
                if c not in criticalities:
                    continue
            out.append((str(rid), str(name), str(rl), str(crit)))
        return out

    def list_latest_value_per_system_for_definition(
        self,
        tenant_id: str,
        kpi_definition_id: str,
        system_ids: list[str],
    ) -> dict[str, tuple[float, datetime]]:
        """Pro System: (value, period_start) des neuesten Eintrags."""
        if not system_ids:
            return {}
        stmt = (
            select(AiSystemKpiValueDB)
            .where(
                AiSystemKpiValueDB.tenant_id == tenant_id,
                AiSystemKpiValueDB.kpi_definition_id == kpi_definition_id,
                AiSystemKpiValueDB.ai_system_id.in_(system_ids),
            )
            .order_by(
                AiSystemKpiValueDB.ai_system_id,
                AiSystemKpiValueDB.period_start.desc(),
            )
        )
        rows = list(self._session.execute(stmt).scalars().all())
        seen: set[str] = set()
        out: dict[str, tuple[float, datetime]] = {}
        for r in rows:
            if r.ai_system_id in seen:
                continue
            seen.add(r.ai_system_id)
            out[r.ai_system_id] = (float(r.value), r.period_start)
        return out

    def list_second_latest_value_per_system(
        self,
        tenant_id: str,
        kpi_definition_id: str,
        system_ids: list[str],
    ) -> dict[str, float]:
        """Pro System: zweitältester period_start-Wert (für Trend auf Portfolio-Ebene)."""
        if not system_ids:
            return {}
        stmt = (
            select(AiSystemKpiValueDB)
            .where(
                AiSystemKpiValueDB.tenant_id == tenant_id,
                AiSystemKpiValueDB.kpi_definition_id == kpi_definition_id,
                AiSystemKpiValueDB.ai_system_id.in_(system_ids),
            )
            .order_by(
                AiSystemKpiValueDB.ai_system_id,
                AiSystemKpiValueDB.period_start.desc(),
            )
        )
        rows = list(self._session.execute(stmt).scalars().all())
        by_sys: dict[str, list[float]] = {}
        for r in rows:
            by_sys.setdefault(r.ai_system_id, []).append(float(r.value))
        out: dict[str, float] = {}
        for sid, vals in by_sys.items():
            if len(vals) >= 2:
                out[sid] = vals[1]
        return out
