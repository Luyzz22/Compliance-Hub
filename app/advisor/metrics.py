"""Advisor metrics aggregation from the in-memory evidence store.

Produces daily-bucketed, PII-free aggregate counts for internal dashboards
and AI Act monitoring obligations.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field

from app.services.rag.evidence_store import (
    list_advisor_agent_events,
    list_rag_events,
)


class AdvisorDailyMetrics(BaseModel):
    date: str
    tenant_id: str
    total_queries: int = 0
    retrieval_mode_bm25: int = 0
    retrieval_mode_hybrid: int = 0
    confidence_high: int = 0
    confidence_medium: int = 0
    confidence_low: int = 0
    agent_answered: int = 0
    agent_escalated: int = 0
    agent_errors: int = 0
    agent_duplicates: int = 0


class AdvisorMetricsResponse(BaseModel):
    tenant_id: str | None
    from_date: str | None
    to_date: str | None
    total_queries: int = 0
    retrieval_mode_distribution: dict[str, int] = Field(default_factory=dict)
    confidence_distribution: dict[str, int] = Field(default_factory=dict)
    escalation_rate: float | None = None
    error_rate: float | None = None
    agent_decision_distribution: dict[str, int] = Field(default_factory=dict)
    channel_distribution: dict[str, int] = Field(default_factory=dict)
    flow_type_distribution: dict[str, int] = Field(default_factory=dict)
    client_id_distribution: dict[str, int] = Field(default_factory=dict)
    latency_p50_ms: float | None = None
    latency_p95_ms: float | None = None
    daily: list[AdvisorDailyMetrics] = Field(default_factory=list)


def _parse_date(iso_str: str | None) -> str | None:
    if not iso_str:
        return None
    try:
        return iso_str[:10]
    except Exception:
        return None


def _in_range(date_str: str | None, from_date: str | None, to_date: str | None) -> bool:
    if date_str is None:
        return True
    if from_date and date_str < from_date:
        return False
    if to_date and date_str > to_date:
        return False
    return True


def aggregate_advisor_metrics(
    *,
    tenant_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 2000,
) -> AdvisorMetricsResponse:
    """Aggregate RAG + agent events into daily metrics buckets.

    Reads from the in-memory evidence store. No PII is accessed or returned.
    """
    tenants = [tenant_id] if tenant_id else _discover_tenants(limit=limit)
    daily_map: dict[tuple[str, str], AdvisorDailyMetrics] = {}
    channel_counts: dict[str, int] = defaultdict(int)
    flow_type_counts: dict[str, int] = defaultdict(int)
    client_id_counts: dict[str, int] = defaultdict(int)
    latencies: list[float] = []

    for tid in tenants:
        _aggregate_rag_events(tid, daily_map, from_date, to_date, limit)
        _aggregate_agent_events(
            tid,
            daily_map,
            from_date,
            to_date,
            limit,
            channel_counts=channel_counts,
            flow_type_counts=flow_type_counts,
            client_id_counts=client_id_counts,
            latencies=latencies,
        )

    daily = sorted(daily_map.values(), key=lambda m: (m.date, m.tenant_id))

    totals = _compute_totals(daily)
    totals["channel_distribution"] = dict(channel_counts)
    totals["flow_type_distribution"] = dict(flow_type_counts)
    totals["client_id_distribution"] = dict(client_id_counts)

    if latencies:
        latencies.sort()
        totals["latency_p50_ms"] = round(_percentile(latencies, 50), 1)
        totals["latency_p95_ms"] = round(_percentile(latencies, 95), 1)

    return AdvisorMetricsResponse(
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
        **totals,
        daily=daily,
    )


def _discover_tenants(*, limit: int) -> list[str]:
    """Discover all tenants with evidence events (lightweight scan)."""
    from app.services.rag.evidence_store import _events, _lock

    with _lock:
        snap = list(_events)

    tenants: set[str] = set()
    for e in snap[-limit:]:
        tid = e.get("tenant_id")
        if tid:
            tenants.add(tid)
    return sorted(tenants)


def _aggregate_rag_events(
    tenant_id: str,
    daily_map: dict[tuple[str, str], AdvisorDailyMetrics],
    from_date: str | None,
    to_date: str | None,
    limit: int,
) -> None:
    events = list_rag_events(tenant_id, limit=limit)
    for e in events:
        day = _parse_date(e.get("recorded_at"))
        if not _in_range(day, from_date, to_date):
            continue
        day = day or "unknown"
        key = (day, tenant_id)
        if key not in daily_map:
            daily_map[key] = AdvisorDailyMetrics(date=day, tenant_id=tenant_id)
        m = daily_map[key]
        m.total_queries += 1

        mode = e.get("retrieval_mode", "bm25")
        if mode == "hybrid":
            m.retrieval_mode_hybrid += 1
        else:
            m.retrieval_mode_bm25 += 1

        conf = e.get("confidence_level", "").lower()
        if conf == "high":
            m.confidence_high += 1
        elif conf == "medium":
            m.confidence_medium += 1
        elif conf == "low":
            m.confidence_low += 1


def _aggregate_agent_events(
    tenant_id: str,
    daily_map: dict[tuple[str, str], AdvisorDailyMetrics],
    from_date: str | None,
    to_date: str | None,
    limit: int,
    *,
    channel_counts: dict[str, int] | None = None,
    flow_type_counts: dict[str, int] | None = None,
    client_id_counts: dict[str, int] | None = None,
    latencies: list[float] | None = None,
) -> None:
    events = list_advisor_agent_events(tenant_id, limit=limit)
    for e in events:
        day = _parse_date(e.get("recorded_at"))
        if not _in_range(day, from_date, to_date):
            continue
        day = day or "unknown"
        key = (day, tenant_id)
        if key not in daily_map:
            daily_map[key] = AdvisorDailyMetrics(date=day, tenant_id=tenant_id)
        m = daily_map[key]

        decision = e.get("decision", "")
        if decision == "answered":
            m.agent_answered += 1
        elif decision == "escalate_to_human":
            m.agent_escalated += 1
        elif decision == "error":
            m.agent_errors += 1
        elif decision == "duplicate":
            m.agent_duplicates += 1

        extra = e.get("extra") or {}
        ch = extra.get("channel", "web")
        if channel_counts is not None:
            channel_counts[ch] = channel_counts.get(ch, 0) + 1

        ft = extra.get("flow_type")
        if ft and flow_type_counts is not None:
            flow_type_counts[ft] = flow_type_counts.get(ft, 0) + 1

        cid = extra.get("client_id")
        if cid and client_id_counts is not None:
            client_id_counts[cid] = client_id_counts.get(cid, 0) + 1

        lat = extra.get("latency_ms")
        if lat is not None and latencies is not None:
            try:
                latencies.append(float(lat))
            except (TypeError, ValueError):
                pass


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_vals):
        return sorted_vals[f]
    return sorted_vals[f] + (k - f) * (sorted_vals[c] - sorted_vals[f])


def _compute_totals(daily: list[AdvisorDailyMetrics]) -> dict[str, Any]:
    total_queries = sum(d.total_queries for d in daily)
    mode_dist: dict[str, int] = defaultdict(int)
    conf_dist: dict[str, int] = defaultdict(int)
    decision_dist: dict[str, int] = defaultdict(int)

    for d in daily:
        mode_dist["bm25"] += d.retrieval_mode_bm25
        mode_dist["hybrid"] += d.retrieval_mode_hybrid
        conf_dist["high"] += d.confidence_high
        conf_dist["medium"] += d.confidence_medium
        conf_dist["low"] += d.confidence_low
        decision_dist["answered"] += d.agent_answered
        decision_dist["escalated"] += d.agent_escalated
        decision_dist["errors"] += d.agent_errors
        decision_dist["duplicates"] += d.agent_duplicates

    total_decisions = (
        decision_dist["answered"] + decision_dist["escalated"] + decision_dist["errors"]
    )
    escalation_rate = (
        round(decision_dist["escalated"] / total_decisions, 4) if total_decisions > 0 else None
    )
    error_rate = (
        round(decision_dist["errors"] / total_decisions, 4) if total_decisions > 0 else None
    )

    return {
        "total_queries": total_queries,
        "retrieval_mode_distribution": dict(mode_dist),
        "confidence_distribution": dict(conf_dist),
        "escalation_rate": escalation_rate,
        "error_rate": error_rate,
        "agent_decision_distribution": dict(decision_dist),
    }
