"""Repository: AI Runtime Events (mandanten- und systemisoliert)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models_db import AiRuntimeEventTable


def _occurred_at_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class AiRuntimeEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists_by_tenant_source_event_id(
        self,
        tenant_id: str,
        source: str,
        source_event_id: str,
    ) -> bool:
        stmt = (
            select(func.count())
            .select_from(AiRuntimeEventTable)
            .where(
                AiRuntimeEventTable.tenant_id == tenant_id,
                AiRuntimeEventTable.source == source,
                AiRuntimeEventTable.source_event_id == source_event_id,
            )
        )
        return int(self._session.execute(stmt).scalar_one() or 0) > 0

    def add(self, row: AiRuntimeEventTable) -> None:
        """Nur Session-Queue; Aufrufer committet (Batch-Ingest)."""
        self._session.add(row)

    def list_in_window(
        self,
        tenant_id: str,
        ai_system_id: str,
        *,
        since: datetime,
        until: datetime | None = None,
    ) -> list[AiRuntimeEventTable]:
        stmt = select(AiRuntimeEventTable).where(
            AiRuntimeEventTable.tenant_id == tenant_id,
            AiRuntimeEventTable.ai_system_id == ai_system_id,
            AiRuntimeEventTable.occurred_at >= since,
        )
        if until is not None:
            stmt = stmt.where(AiRuntimeEventTable.occurred_at <= until)
        stmt = stmt.order_by(AiRuntimeEventTable.occurred_at.asc())
        return list(self._session.execute(stmt).scalars().all())

    def aggregate_for_oami(
        self,
        tenant_id: str,
        ai_system_id: str,
        *,
        since: datetime,
        until: datetime,
    ) -> dict[str, object]:
        """Rohzahlen für OAMI-Berechnung (Python-seitig)."""
        rows = self.list_in_window(tenant_id, ai_system_id, since=since, until=until)
        if not rows:
            return {
                "event_count": 0,
                "last_occurred_at": None,
                "distinct_days": 0,
                "incident_high": 0,
                "breach_count": 0,
                "incident_count": 0,
            }
        last_at = max(_occurred_at_utc(r.occurred_at) for r in rows)
        days: set[str] = set()
        incident_high = 0
        breach_count = 0
        incident_count = 0
        sev_hi = frozenset({"high", "critical"})
        for r in rows:
            d = _occurred_at_utc(r.occurred_at).date().isoformat()
            days.add(d)
            et = str(r.event_type).lower()
            if et == "incident":
                incident_count += 1
                if (r.severity or "").lower() in sev_hi:
                    incident_high += 1
            if et == "metric_threshold_breach":
                breach_count += 1
        return {
            "event_count": len(rows),
            "last_occurred_at": last_at,
            "distinct_days": len(days),
            "incident_high": incident_high,
            "breach_count": breach_count,
            "incident_count": incident_count,
        }

    def list_system_ids_with_events(
        self,
        tenant_id: str,
        *,
        since: datetime,
        until: datetime,
    ) -> list[str]:
        stmt = (
            select(AiRuntimeEventTable.ai_system_id)
            .where(
                AiRuntimeEventTable.tenant_id == tenant_id,
                AiRuntimeEventTable.occurred_at >= since,
                AiRuntimeEventTable.occurred_at <= until,
            )
            .distinct()
        )
        return [str(x) for x in self._session.execute(stmt).scalars().all()]

    def refresh_incident_summary(
        self,
        *,
        tenant_id: str,
        ai_system_id: str,
        window_start: datetime,
        window_end: datetime,
        summary_id: str,
    ) -> None:
        """Materialisiert eine Zeile ai_runtime_incident_summaries aus Events im Fenster."""
        from app.models_db import AiRuntimeIncidentSummaryTable

        rows = self.list_in_window(tenant_id, ai_system_id, since=window_start, until=window_end)
        inc = [r for r in rows if str(r.event_type).lower() == "incident"]
        high = 0
        last_i: datetime | None = None
        sev_hi = frozenset({"high", "critical"})
        for r in inc:
            if (r.severity or "").lower() in sev_hi:
                high += 1
            oa = _occurred_at_utc(r.occurred_at)
            if last_i is None or oa > _occurred_at_utc(last_i):
                last_i = oa
        stmt = select(AiRuntimeIncidentSummaryTable).where(
            AiRuntimeIncidentSummaryTable.tenant_id == tenant_id,
            AiRuntimeIncidentSummaryTable.ai_system_id == ai_system_id,
            AiRuntimeIncidentSummaryTable.window_start == window_start,
            AiRuntimeIncidentSummaryTable.window_end == window_end,
        )
        existing = self._session.execute(stmt).scalar_one_or_none()
        now = datetime.now(UTC)
        if existing is None:
            row = AiRuntimeIncidentSummaryTable(
                id=summary_id,
                tenant_id=tenant_id,
                ai_system_id=ai_system_id,
                window_start=window_start,
                window_end=window_end,
                incident_count=len(inc),
                high_severity_count=high,
                last_incident_at=last_i,
                computed_at_utc=now,
            )
            self._session.add(row)
        else:
            existing.incident_count = len(inc)
            existing.high_severity_count = high
            existing.last_incident_at = last_i
            existing.computed_at_utc = now
        self._session.flush()
