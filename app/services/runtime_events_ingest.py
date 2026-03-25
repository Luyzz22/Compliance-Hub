"""Ingest normalisierter AI-Runtime-Events (SAP AI Core u. a.)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models_db import AiRuntimeEventTable
from app.operational_monitoring_models import RuntimeEventIn, RuntimeEventsIngestResult
from app.repositories.ai_kpis import AiKpiRepository
from app.repositories.ai_runtime_events import AiRuntimeEventRepository
from app.services.runtime_event_sanitize import sanitize_runtime_event_extra


def _day_bounds_utc(dt: datetime) -> tuple[datetime, datetime]:
    d = dt.astimezone(UTC).date()
    start = datetime(d.year, d.month, d.day, tzinfo=UTC)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    return start, end


def _maybe_upsert_kpi_from_event(
    session: Session,
    *,
    tenant_id: str,
    ai_system_id: str,
    ev: RuntimeEventIn,
) -> bool:
    if ev.value is None or ev.metric_key is None:
        return False
    if str(ev.event_type) not in ("metric_snapshot", "metric_threshold_breach"):
        return False
    repo = AiKpiRepository(session)
    definition = repo.get_definition_by_key(ev.metric_key.strip())
    if definition is None:
        return False
    start, end = _day_bounds_utc(ev.occurred_at)
    repo.upsert_value(
        tenant_id=tenant_id,
        ai_system_id=ai_system_id,
        kpi_definition_id=definition.id,
        period_start=start,
        period_end=end,
        value=float(ev.value),
        source="runtime_ingest",
        comment=None,
        new_id=str(uuid.uuid4()),
        commit=False,
    )
    return True


def ingest_runtime_events(
    session: Session,
    *,
    tenant_id: str,
    ai_system_id: str,
    events: list[RuntimeEventIn],
    refresh_incident_summary: bool = True,
) -> RuntimeEventsIngestResult:
    """
    Validiert und persistiert Events. Idempotenz über (tenant_id, source_event_id).

    Optional: KPI-Zeitreihe bei bekanntem metric_key + metric_snapshot/-breach.
    """
    repo = AiRuntimeEventRepository(session)
    inserted = 0
    skipped = 0
    kpi_updates = 0
    now = datetime.now(UTC)
    window_start = now - timedelta(days=90)
    window_end = now
    batch_seen: set[str] = set()

    try:
        for ev in events:
            sid = ev.source_event_id.strip()
            if sid in batch_seen:
                skipped += 1
                continue
            if repo.exists_by_source_event_id(tenant_id, sid):
                skipped += 1
                continue
            batch_seen.add(sid)
            extra = sanitize_runtime_event_extra(ev.extra if isinstance(ev.extra, dict) else {})
            row = AiRuntimeEventTable(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                ai_system_id=ai_system_id,
                source=str(ev.source)[:64],
                source_event_id=sid[:128],
                event_type=str(ev.event_type)[:64],
                severity=(ev.severity[:32] if ev.severity else None),
                metric_key=(ev.metric_key[:128] if ev.metric_key else None),
                incident_code=(ev.incident_code[:128] if ev.incident_code else None),
                value=ev.value,
                delta=ev.delta,
                threshold_breached=ev.threshold_breached,
                environment=(ev.environment[:64] if ev.environment else None),
                model_version=(ev.model_version[:255] if ev.model_version else None),
                occurred_at=ev.occurred_at.astimezone(UTC)
                if ev.occurred_at.tzinfo
                else ev.occurred_at.replace(tzinfo=UTC),
                received_at=now,
                extra=extra,
            )
            repo.add(row)
            inserted += 1
            if _maybe_upsert_kpi_from_event(
                session,
                tenant_id=tenant_id,
                ai_system_id=ai_system_id,
                ev=ev,
            ):
                kpi_updates += 1

        if inserted > 0:
            session.flush()
            if refresh_incident_summary:
                repo.refresh_incident_summary(
                    tenant_id=tenant_id,
                    ai_system_id=ai_system_id,
                    window_start=window_start,
                    window_end=window_end,
                    summary_id=str(uuid.uuid4()),
                )
            session.commit()

        return RuntimeEventsIngestResult(
            inserted=inserted,
            skipped_duplicate=skipped,
            kpi_updates=kpi_updates,
        )
    except Exception:
        session.rollback()
        raise
