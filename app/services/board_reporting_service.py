"""Deterministic board reporting aggregation from governance and operations signals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_db import (
    AISystemTable,
    GovernanceControlEvidenceTable,
    GovernanceControlReviewTable,
    GovernanceControlTable,
    Nis2IncidentTable,
    ServiceHealthIncidentTable,
)


TrendDirection = Literal["up", "down", "stable"]
TrafficLight = Literal["green", "amber", "red"]


@dataclass(slots=True)
class BoardMetric:
    metric_key: str
    label: str
    value: float
    unit: str
    traffic_light: TrafficLight
    trend_direction: TrendDirection
    trend_delta: float
    narrative_de: str


@dataclass(slots=True)
class BoardSnapshot:
    metrics: list[BoardMetric]
    top_risk_areas: list[str]
    resilience_summary_de: str
    headline_de: str


def _traffic_by_threshold(value: float, *, amber_from: float, red_from: float) -> TrafficLight:
    if value >= red_from:
        return "red"
    if value >= amber_from:
        return "amber"
    return "green"


def _trend(curr: float, prev: float, *, stable_delta: float = 0.5) -> tuple[TrendDirection, float]:
    delta = round(curr - prev, 2)
    if abs(delta) <= stable_delta:
        return "stable", delta
    if delta > 0:
        return "up", delta
    return "down", delta


async def _scalar_int(session: AsyncSession, stmt: Select[tuple[int]]) -> int:
    raw = await session.scalar(stmt)
    return int(raw or 0)


async def compute_snapshot(
    session: AsyncSession,
    *,
    tenant_id: str,
    period_start: datetime,
    period_end: datetime,
    prev_start: datetime,
    prev_end: datetime,
) -> BoardSnapshot:
    # 1) overall governance readiness %
    active_controls_stmt = select(func.count()).where(
        GovernanceControlTable.tenant_id == tenant_id,
    )
    active_controls = await _scalar_int(session, active_controls_stmt)
    ready_controls_stmt = select(func.count()).where(
        GovernanceControlTable.tenant_id == tenant_id,
        GovernanceControlTable.status.in_(["implemented", "in_review"]),
    )
    ready_controls = await _scalar_int(session, ready_controls_stmt)
    readiness_pct = round(100.0 if active_controls == 0 else (ready_controls * 100.0 / active_controls), 1)

    prev_ready_controls_stmt = select(func.count()).where(
        GovernanceControlTable.tenant_id == tenant_id,
        GovernanceControlTable.status.in_(["implemented", "in_review"]),
        GovernanceControlTable.updated_at_utc <= prev_end,
    )
    prev_ready_controls = await _scalar_int(session, prev_ready_controls_stmt)
    prev_readiness_pct = round(
        100.0 if active_controls == 0 else (prev_ready_controls * 100.0 / active_controls),
        1,
    )
    readiness_trend, readiness_delta = _trend(readiness_pct, prev_readiness_pct, stable_delta=1.0)

    # 2) open critical controls
    critical_control_filter = or_(
        GovernanceControlTable.status.in_(["overdue", "needs_review"]),
        GovernanceControlTable.framework_tags_json.like("%NIS2%"),
    )
    open_critical_controls = await _scalar_int(
        session,
        select(func.count()).where(
            GovernanceControlTable.tenant_id == tenant_id,
            critical_control_filter,
            GovernanceControlTable.status != "implemented",
        ),
    )
    prev_open_critical_controls = await _scalar_int(
        session,
        select(func.count()).where(
            GovernanceControlTable.tenant_id == tenant_id,
            critical_control_filter,
            GovernanceControlTable.updated_at_utc <= prev_end,
            GovernanceControlTable.status != "implemented",
        ),
    )
    open_controls_trend, open_controls_delta = _trend(
        open_critical_controls,
        prev_open_critical_controls,
        stable_delta=1.0,
    )

    # 3) evidence gaps count = controls without evidence
    evidence_gaps_stmt = (
        select(func.count())
        .select_from(GovernanceControlTable)
        .where(
            GovernanceControlTable.tenant_id == tenant_id,
            ~GovernanceControlTable.id.in_(
                select(GovernanceControlEvidenceTable.control_id).where(
                    GovernanceControlEvidenceTable.tenant_id == tenant_id,
                )
            ),
        )
    )
    evidence_gaps = await _scalar_int(session, evidence_gaps_stmt)
    prev_evidence_gaps = await _scalar_int(
        session,
        evidence_gaps_stmt.where(GovernanceControlTable.updated_at_utc <= prev_end),
    )
    evidence_trend, evidence_delta = _trend(evidence_gaps, prev_evidence_gaps, stable_delta=1.0)

    # 4) overdue reviews
    overdue_reviews = await _scalar_int(
        session,
        select(func.count()).where(
            GovernanceControlReviewTable.tenant_id == tenant_id,
            GovernanceControlReviewTable.completed_at.is_(None),
            GovernanceControlReviewTable.due_at < period_end,
        ),
    )
    prev_overdue_reviews = await _scalar_int(
        session,
        select(func.count()).where(
            GovernanceControlReviewTable.tenant_id == tenant_id,
            GovernanceControlReviewTable.completed_at.is_(None),
            GovernanceControlReviewTable.due_at < prev_end,
        ),
    )
    overdue_trend, overdue_delta = _trend(overdue_reviews, prev_overdue_reviews, stable_delta=1.0)

    # 5) open critical incidents (operations + NIS2)
    open_critical_ops_incidents = await _scalar_int(
        session,
        select(func.count()).where(
            ServiceHealthIncidentTable.tenant_id == tenant_id,
            ServiceHealthIncidentTable.incident_state == "open",
            ServiceHealthIncidentTable.severity == "critical",
        ),
    )
    open_nis2_incidents = await _scalar_int(
        session,
        select(func.count()).where(
            Nis2IncidentTable.tenant_id == tenant_id,
            Nis2IncidentTable.workflow_status.in_(["detected", "reported", "contained"]),
            Nis2IncidentTable.severity.in_(["high", "critical"]),
        ),
    )
    open_critical_incidents = open_critical_ops_incidents + open_nis2_incidents
    prev_open_critical_incidents = await _scalar_int(
        session,
        select(func.count()).where(
            ServiceHealthIncidentTable.tenant_id == tenant_id,
            ServiceHealthIncidentTable.incident_state == "open",
            ServiceHealthIncidentTable.severity == "critical",
            ServiceHealthIncidentTable.detected_at <= prev_end,
        ),
    )
    incidents_trend, incidents_delta = _trend(
        open_critical_incidents,
        prev_open_critical_incidents,
        stable_delta=1.0,
    )

    # 6) AI high risk systems
    high_risk_systems = await _scalar_int(
        session,
        select(func.count()).where(
            AISystemTable.tenant_id == tenant_id,
            func.lower(AISystemTable.risk_level).in_(["high", "high_risk"]),
        ),
    )
    prev_high_risk_systems = await _scalar_int(
        session,
        select(func.count()).where(
            AISystemTable.tenant_id == tenant_id,
            func.lower(AISystemTable.risk_level).in_(["high", "high_risk"]),
            AISystemTable.updated_at_utc <= prev_end,
        ),
    )
    ai_risk_trend, ai_risk_delta = _trend(
        high_risk_systems,
        prev_high_risk_systems,
        stable_delta=0.0,
    )

    # 7) NIS2 exposure level derived from incident density
    nis2_exposure_level = (
        "high"
        if open_critical_incidents >= 5
        else "medium"
        if open_critical_incidents >= 2
        else "low"
    )

    metrics = [
        BoardMetric(
            metric_key="overall_governance_readiness_pct",
            label="Governance Readiness",
            value=readiness_pct,
            unit="percent",
            traffic_light=(
                "green"
                if readiness_pct >= 85
                else "amber"
                if readiness_pct >= 70
                else "red"
            ),
            trend_direction=readiness_trend,
            trend_delta=readiness_delta,
            narrative_de=(
                "Anteil umgesetzter Controls (implemented/in_review) "
                "im Tenant-Control-Register."
            ),
        ),
        BoardMetric(
            metric_key="open_critical_controls",
            label="Open Critical Controls",
            value=float(open_critical_controls),
            unit="count",
            traffic_light=_traffic_by_threshold(open_critical_controls, amber_from=3, red_from=8),
            trend_direction=open_controls_trend,
            trend_delta=open_controls_delta,
            narrative_de="Überfällige oder NIS2-relevante Controls, die noch nicht umgesetzt sind.",
        ),
        BoardMetric(
            metric_key="evidence_gaps_count",
            label="Evidence Gaps",
            value=float(evidence_gaps),
            unit="count",
            traffic_light=_traffic_by_threshold(evidence_gaps, amber_from=5, red_from=15),
            trend_direction=evidence_trend,
            trend_delta=evidence_delta,
            narrative_de="Controls ohne hinterlegte Evidence-Einträge (deterministische Zählung).",
        ),
        BoardMetric(
            metric_key="overdue_reviews_count",
            label="Overdue Reviews",
            value=float(overdue_reviews),
            unit="count",
            traffic_light=_traffic_by_threshold(overdue_reviews, amber_from=3, red_from=10),
            trend_direction=overdue_trend,
            trend_delta=overdue_delta,
            narrative_de="Offene Reviews mit überschrittenem Due Date.",
        ),
        BoardMetric(
            metric_key="open_critical_incidents",
            label="Open Critical Incidents",
            value=float(open_critical_incidents),
            unit="count",
            traffic_light=_traffic_by_threshold(open_critical_incidents, amber_from=1, red_from=3),
            trend_direction=incidents_trend,
            trend_delta=incidents_delta,
            narrative_de="Summe aus offenen kritischen Service-Health- und NIS2-Incidents.",
        ),
        BoardMetric(
            metric_key="ai_high_risk_systems_count",
            label="AI High-Risk Systems",
            value=float(high_risk_systems),
            unit="count",
            traffic_light=_traffic_by_threshold(high_risk_systems, amber_from=3, red_from=8),
            trend_direction=ai_risk_trend,
            trend_delta=ai_risk_delta,
            narrative_de="Anzahl AI-Systeme mit Risk-Level HIGH/HIGH_RISK im Register.",
        ),
    ]

    top_risk_areas: list[str] = []
    if open_critical_controls >= 5:
        top_risk_areas.append("Control-Backlog in kritischen Domänen (NIS2/ISO)")
    if evidence_gaps >= 8:
        top_risk_areas.append("Nachweislage lückenhaft (Evidence Gaps)")
    if open_critical_incidents >= 2:
        top_risk_areas.append("Operational Resilience unter Druck (offene kritische Incidents)")
    if not top_risk_areas:
        top_risk_areas.append("Keine dominant kritische Exposure-Area im aktuellen Zeitraum")

    resilience_summary_de = (
        f"Resilience-Lage: {open_critical_incidents} offene kritische Incidents, "
        f"NIS2-Exposure {nis2_exposure_level.upper()}."
    )
    headline_de = (
        f"Board Pack {period_end.strftime('%m/%Y')}: Readiness {readiness_pct}%, "
        f"{open_critical_controls} kritische offene Controls, "
        f"{evidence_gaps} Evidence-Gaps."
    )
    return BoardSnapshot(
        metrics=metrics,
        top_risk_areas=top_risk_areas,
        resilience_summary_de=resilience_summary_de,
        headline_de=headline_de,
    )


async def derive_period_bounds(
    period_start: datetime, period_end: datetime
) -> tuple[datetime, datetime]:
    prev_end = period_start
    prev_start = prev_end - (period_end - period_start)
    if prev_start >= prev_end:
        prev_start = prev_end.replace(tzinfo=UTC) if prev_end.tzinfo is None else prev_end
    return prev_start, prev_end

