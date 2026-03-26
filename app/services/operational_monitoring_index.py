"""Operational AI Monitoring Index (OAMI) – erklärbare Teilscores, System- und Tenant-Ebene."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models_db import TenantOperationalMonitoringSnapshotTable
from app.operational_monitoring_models import (
    OamiComponentsOut,
    OamiLevel,
    SystemMonitoringIndexOut,
    TenantOperationalMonitoringIndexOut,
)
from app.repositories.ai_runtime_events import AiRuntimeEventRepository
from app.repositories.ai_systems import AISystemRepository
from app.services.oami_explanation import explain_system_oami_de, explain_tenant_oami_de

logger = logging.getLogger(__name__)

# Kalibrierung gemäß docs/governance-operational-ai-monitoring.md (Abschn. 3.2)
_OAMI_WEIGHTS = (0.25, 0.25, 0.35, 0.15)  # freshness, coverage, incident, stability


def _level_from_index(score: int) -> OamiLevel:
    if score < 40:
        return "low"
    if score < 70:
        return "medium"
    return "high"


def _freshness_component(last_occurred_at: datetime | None, now: datetime) -> float:
    if last_occurred_at is None:
        return 0.0
    age_days = (now - last_occurred_at.astimezone(UTC)).total_seconds() / 86400.0
    if age_days <= 3.0:
        return 1.0
    if age_days >= 14.0:
        return 0.0
    return max(0.0, 1.0 - (age_days - 3.0) / 11.0)


def _coverage_component(distinct_days: int, window_days: int) -> float:
    """Sättigung nach überschaubarer Aktivität (nicht erst nach 90/90 Tagen)."""
    if window_days <= 0:
        return 0.0
    d_sat = min(window_days, 30)
    return min(1.0, float(distinct_days) / float(max(1, d_sat)))


def _incident_component(
    incident_count: int,
    incident_high: int,
    *,
    safety_violation_incidents: int = 0,
) -> float:
    """Ohne Ticket-Workflow: weniger Incidents und weniger high/critical = besser.

    Zusätzlich: ``safety_violation``-Subtype (stärker gewichtet, Board/OAMI-relevant).
    """
    penalty = min(
        1.0,
        incident_high * 0.22
        + max(0, incident_count - incident_high) * 0.07
        + safety_violation_incidents * 0.12,
    )
    return max(0.0, 1.0 - penalty)


def _stability_component(breach_count: int, window_days: int) -> float:
    scale = max(3.0, (window_days / 30.0) * 5.0)
    penalty = min(1.0, float(breach_count) / scale)
    return max(0.0, 1.0 - penalty)


def _components_from_agg(
    agg: dict[str, object],
    *,
    now: datetime,
    window_days: int,
) -> tuple[OamiComponentsOut, int, bool]:
    event_count = int(agg.get("event_count") or 0)
    has_data = event_count > 0
    last_at = agg.get("last_occurred_at")
    last_dt = last_at if isinstance(last_at, datetime) else None
    distinct_days = int(agg.get("distinct_days") or 0)
    incident_high = int(agg.get("incident_high") or 0)
    breach_count = int(agg.get("breach_count") or 0)
    incident_count = int(agg.get("incident_count") or 0)
    raw_sub = agg.get("incident_count_by_subtype")
    incident_by_subtype: dict[str, int] = dict(raw_sub) if isinstance(raw_sub, dict) else {}
    safety_sv = int(incident_by_subtype.get("safety_violation", 0))

    f = _freshness_component(last_dt, now)
    c = _coverage_component(distinct_days, window_days)
    i = _incident_component(
        incident_count,
        incident_high,
        safety_violation_incidents=safety_sv,
    )
    s = _stability_component(breach_count, window_days)

    if not has_data:
        z = OamiComponentsOut(
            freshness=0.0,
            activity_days=0.0,
            incident_stability=0.0,
            metric_stability=0.0,
        )
        return z, 0, False

    oami_01 = (
        _OAMI_WEIGHTS[0] * f + _OAMI_WEIGHTS[1] * c + _OAMI_WEIGHTS[2] * i + _OAMI_WEIGHTS[3] * s
    )
    score = int(round(100.0 * max(0.0, min(1.0, oami_01))))
    comp = OamiComponentsOut(
        freshness=f,
        activity_days=c,
        incident_stability=i,
        metric_stability=s,
    )
    return comp, score, True


def compute_system_monitoring_index(
    session: Session,
    tenant_id: str,
    ai_system_id: str,
    *,
    window_days: int = 90,
) -> SystemMonitoringIndexOut:
    now = datetime.now(UTC)
    since = now - timedelta(days=window_days)
    ev_repo = AiRuntimeEventRepository(session)
    agg = ev_repo.aggregate_for_oami(tenant_id, ai_system_id, since=since, until=now)
    comp, score, has_data = _components_from_agg(agg, now=now, window_days=window_days)
    last_at = agg.get("last_occurred_at")
    last_dt = last_at if isinstance(last_at, datetime) else None

    raw_sub = agg.get("incident_count_by_subtype")
    inc_sub: dict[str, int] = dict(raw_sub) if isinstance(raw_sub, dict) else {}

    base = SystemMonitoringIndexOut(
        ai_system_id=ai_system_id,
        tenant_id=tenant_id,
        window_days=window_days,
        operational_monitoring_index=score,
        level=_level_from_index(score),
        has_data=has_data,
        last_event_at=last_dt,
        incident_count=int(agg.get("incident_count") or 0),
        high_severity_incident_count=int(agg.get("incident_high") or 0),
        incident_count_by_subtype=inc_sub,
        metric_threshold_breach_count=int(agg.get("breach_count") or 0),
        distinct_active_days=int(agg.get("distinct_days") or 0),
        components=comp,
        explanation=None,
    )
    return base.model_copy(update={"explanation": explain_system_oami_de(base)})


def _risk_weight(risk_level: str | None) -> float:
    r = (risk_level or "minimal").lower().replace(" ", "_")
    table = {
        "unacceptable": 4.0,
        "high": 3.0,
        "limited": 2.0,
        "minimal": 1.0,
    }
    return table.get(r, 1.5)


def compute_tenant_operational_monitoring_index(
    session: Session,
    tenant_id: str,
    *,
    window_days: int = 90,
    persist_snapshot: bool = False,
) -> TenantOperationalMonitoringIndexOut:
    """
    Risikogewichteter Mittelwert der System-OAMIs (nur Systeme mit Events im Fenster).

    Optional: Schreibt tenant_operational_monitoring_snapshots (Hintergrund-Job / Warm-Cache).
    """
    now = datetime.now(UTC)
    since = now - timedelta(days=window_days)
    ev_repo = AiRuntimeEventRepository(session)
    sys_repo = AISystemRepository(session)
    system_ids = ev_repo.list_system_ids_with_events(tenant_id, since=since, until=now)
    if not system_ids:
        out = TenantOperationalMonitoringIndexOut(
            tenant_id=tenant_id,
            window_days=window_days,
            operational_monitoring_index=0,
            level="low",
            systems_scored=0,
            has_any_runtime_data=False,
            components=None,
            explanation=None,
        )
        out = out.model_copy(update={"explanation": explain_tenant_oami_de(out)})
        if persist_snapshot:
            _persist_tenant_snapshot(session, tenant_id, window_days, out, now)
        logger.info(
            "oami_compute tenant_id=%s window_days=%s systems_scored=0 index=0 persist=%s",
            tenant_id,
            window_days,
            persist_snapshot,
        )
        return out

    weighted_index = 0.0
    wf = wc = wi = ws = 0.0
    w_sum = 0.0

    for sid in system_ids:
        system = sys_repo.get_by_id(tenant_id, sid)
        w = _risk_weight(system.risk_level if system else None)
        agg = ev_repo.aggregate_for_oami(tenant_id, sid, since=since, until=now)
        comp, score, _has = _components_from_agg(agg, now=now, window_days=window_days)
        weighted_index += w * float(score)
        wf += w * comp.freshness
        wc += w * comp.activity_days
        wi += w * comp.incident_stability
        ws += w * comp.metric_stability
        w_sum += w

    if w_sum <= 0:
        w_sum = 1.0
    idx = int(round(weighted_index / w_sum))
    idx = max(0, min(100, idx))
    comp_t = OamiComponentsOut(
        freshness=wf / w_sum,
        activity_days=wc / w_sum,
        incident_stability=wi / w_sum,
        metric_stability=ws / w_sum,
    )
    out = TenantOperationalMonitoringIndexOut(
        tenant_id=tenant_id,
        window_days=window_days,
        operational_monitoring_index=idx,
        level=_level_from_index(idx),
        systems_scored=len(system_ids),
        has_any_runtime_data=True,
        components=comp_t,
        explanation=None,
    )
    out = out.model_copy(update={"explanation": explain_tenant_oami_de(out)})
    if persist_snapshot:
        _persist_tenant_snapshot(session, tenant_id, window_days, out, now)
    logger.info(
        "oami_compute tenant_id=%s window_days=%s systems_scored=%s index=%s persist=%s",
        tenant_id,
        window_days,
        len(system_ids),
        idx,
        persist_snapshot,
    )
    return out


def _persist_tenant_snapshot(
    session: Session,
    tenant_id: str,
    window_days: int,
    result: TenantOperationalMonitoringIndexOut,
    computed_at: datetime,
) -> None:
    breakdown: dict[str, object] = {
        "systems_scored": result.systems_scored,
        "has_any_runtime_data": result.has_any_runtime_data,
    }
    if result.components is not None:
        breakdown["components"] = result.components.model_dump()
    row = session.get(
        TenantOperationalMonitoringSnapshotTable,
        (tenant_id, window_days),
    )
    if row is None:
        row = TenantOperationalMonitoringSnapshotTable(
            tenant_id=tenant_id,
            window_days=window_days,
            index_value=result.operational_monitoring_index,
            level=result.level,
            breakdown_json=breakdown,
            computed_at_utc=computed_at,
        )
        session.add(row)
    else:
        row.index_value = result.operational_monitoring_index
        row.level = result.level
        row.breakdown_json = breakdown
        row.computed_at_utc = computed_at
    session.commit()


def _snap_int(d: dict | None, key: str) -> int:
    if not d:
        return 0
    v = d.get(key, 0)
    return int(v) if v is not None else 0


def _snap_bool(d: dict | None, key: str) -> bool:
    if not d:
        return False
    return bool(d.get(key))


def read_tenant_oami_snapshot(
    session: Session,
    tenant_id: str,
    window_days: int,
) -> TenantOperationalMonitoringIndexOut | None:
    """Liest materialisierten Tenant-OAMI, falls vorhanden (schnelle GET ohne Reaggregation)."""
    row = session.get(TenantOperationalMonitoringSnapshotTable, (tenant_id, window_days))
    if row is None:
        return None
    comp_raw = row.breakdown_json.get("components") if row.breakdown_json else None
    comp = OamiComponentsOut.model_validate(comp_raw) if isinstance(comp_raw, dict) else None
    lvl: OamiLevel = row.level if row.level in ("low", "medium", "high") else "low"
    return TenantOperationalMonitoringIndexOut(
        tenant_id=tenant_id,
        window_days=window_days,
        operational_monitoring_index=int(row.index_value),
        level=lvl,
        systems_scored=_snap_int(row.breakdown_json, "systems_scored"),
        has_any_runtime_data=_snap_bool(row.breakdown_json, "has_any_runtime_data"),
        components=comp,
    )
