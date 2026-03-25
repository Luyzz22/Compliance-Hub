"""Orchestrierung: AI-KPI-Listen, Upsert, Mandanten-Summary, Board-Report-Kontext."""

from __future__ import annotations

import uuid
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

from sqlalchemy.orm import Session

from app.ai_compliance_board_report_models import (
    BoardReportKpiPortfolioRowBrief,
    BoardReportKpiSystemRowBrief,
    BoardReportSystemKpiValueBrief,
)
from app.ai_kpi_models import (
    AiKpiDefinitionRead,
    AiKpiPerKpiAggregateRead,
    AiKpiSummaryResponse,
    AiSystemCriticalKpiRead,
    AiSystemCriticalRowRead,
    AiSystemKpiSeriesRead,
    AiSystemKpisListResponse,
    AiSystemKpiUpsertResponse,
    AiSystemKpiValueRead,
)
from app.models_db import AiKpiDefinitionDB, AiSystemKpiValueDB
from app.repositories.ai_kpis import AiKpiRepository
from app.services.ai_kpi_analytics import (
    kpi_value_status,
    mean_or_none,
    numeric_trend,
    trend_from_series,
)


def _def_read(row: AiKpiDefinitionDB) -> AiKpiDefinitionRead:
    tags = row.framework_tags if isinstance(row.framework_tags, list) else []
    rd = str(row.recommended_direction).lower()
    if rd not in ("up", "down"):
        rd = "down"
    return AiKpiDefinitionRead(
        id=row.id,
        key=row.key,
        name=row.name,
        description=row.description,
        category=row.category,
        unit=row.unit,
        recommended_direction=rd,  # type: ignore[arg-type]
        framework_tags=[str(x) for x in tags],
    )


def list_kpis_for_ai_system(
    session: Session,
    tenant_id: str,
    ai_system_id: str,
) -> AiSystemKpisListResponse:
    repo = AiKpiRepository(session)
    defs = {d.id: d for d in repo.list_definitions()}
    raw_values = repo.list_values_for_system(tenant_id, ai_system_id)
    by_def: dict[str, list[AiSystemKpiValueDB]] = defaultdict(list)
    for v in raw_values:
        by_def[v.kpi_definition_id].append(v)

    series_out: list[AiSystemKpiSeriesRead] = []
    for def_id, def_row in defs.items():
        vals = by_def.get(def_id, [])
        vals_sorted = sorted(vals, key=lambda x: x.period_start)
        periods = [
            AiSystemKpiValueRead(
                id=v.id,
                period_start=v.period_start,
                period_end=v.period_end,
                value=float(v.value),
                source=v.source,
                comment=v.comment,
            )
            for v in reversed(vals_sorted)
        ]
        pairs = [(v.period_start, float(v.value)) for v in vals_sorted]
        tr = trend_from_series(pairs)
        latest_v = float(vals_sorted[-1].value) if vals_sorted else 0.0
        st = (
            kpi_value_status(
                latest_v,
                def_row.recommended_direction,
                def_row.alert_threshold_high,
                def_row.alert_threshold_low,
            )
            if vals_sorted
            else "ok"
        )
        series_out.append(
            AiSystemKpiSeriesRead(
                definition=_def_read(def_row),
                periods=periods,
                trend=tr,
                latest_status=st,
            ),
        )
    series_out.sort(key=lambda s: s.definition.key)
    return AiSystemKpisListResponse(ai_system_id=ai_system_id, series=series_out)


def upsert_kpi_value(
    session: Session,
    tenant_id: str,
    ai_system_id: str,
    *,
    kpi_definition_id: str,
    period_start: datetime,
    period_end: datetime,
    value: float,
    source: str,
    comment: str | None,
) -> AiSystemKpiUpsertResponse:
    repo = AiKpiRepository(session)
    if repo.get_definition(kpi_definition_id) is None:
        raise ValueError("Unknown kpi_definition_id")
    row = repo.upsert_value(
        tenant_id=tenant_id,
        ai_system_id=ai_system_id,
        kpi_definition_id=kpi_definition_id,
        period_start=period_start,
        period_end=period_end,
        value=value,
        source=source,
        comment=comment,
        new_id=str(uuid.uuid4()),
    )
    return AiSystemKpiUpsertResponse(
        id=row.id,
        kpi_definition_id=row.kpi_definition_id,
        period_start=row.period_start,
        period_end=row.period_end,
        value=float(row.value),
        source=row.source,
        comment=row.comment,
    )


def _parse_criticality_filter(raw: str | None) -> frozenset[str] | None:
    if not raw or not str(raw).strip():
        return None
    parts = {p.strip().lower() for p in str(raw).split(",") if p.strip()}
    return frozenset(parts) if parts else None


def _defs_for_framework(
    defs: Iterable[AiKpiDefinitionDB],
    framework_key: str | None,
) -> list[AiKpiDefinitionDB]:
    if not framework_key or not str(framework_key).strip():
        return list(defs)
    fk = str(framework_key).strip().lower()
    out: list[AiKpiDefinitionDB] = []
    for d in defs:
        tags = d.framework_tags if isinstance(d.framework_tags, list) else []
        if fk in {str(t).lower() for t in tags}:
            out.append(d)
    return out


def build_ai_kpi_summary(
    session: Session,
    tenant_id: str,
    *,
    framework_key: str | None = None,
    criticality: str | None = None,
) -> AiKpiSummaryResponse:
    repo = AiKpiRepository(session)
    crit_f = _parse_criticality_filter(criticality)
    systems = repo.list_high_risk_system_ids(tenant_id, criticalities=crit_f)
    system_ids = [s[0] for s in systems]
    id_to_meta = {s[0]: (s[1], s[2], s[3]) for s in systems}

    all_defs = repo.list_definitions()
    defs = _defs_for_framework(all_defs, framework_key)

    per_kpi: list[AiKpiPerKpiAggregateRead] = []
    per_system_critical: list[AiSystemCriticalRowRead] = []

    for d in defs:
        latest_map = repo.list_latest_value_per_system_for_definition(
            tenant_id,
            d.id,
            system_ids,
        )
        prev_map = repo.list_second_latest_value_per_system(
            tenant_id,
            d.id,
            system_ids,
        )
        latest_vals = [v for _, (v, _) in latest_map.items()]
        paired_prev: list[float] = []
        paired_latest: list[float] = []
        for sid, (lv, _) in latest_map.items():
            if sid in prev_map:
                paired_latest.append(lv)
                paired_prev.append(prev_map[sid])

        m_latest = mean_or_none(latest_vals)
        m_prev = mean_or_none(paired_prev)
        agg_trend = (
            numeric_trend(m_prev, m_latest)
            if m_latest is not None and m_prev is not None
            else "flat"
        )

        per_kpi.append(
            AiKpiPerKpiAggregateRead(
                kpi_key=d.key,
                name=d.name,
                unit=d.unit,
                category=d.category,
                avg_latest=m_latest,
                min_latest=min(latest_vals) if latest_vals else None,
                max_latest=max(latest_vals) if latest_vals else None,
                trend=agg_trend,
                systems_with_data=len(latest_vals),
            ),
        )

    critical_by_system: dict[str, list[AiSystemCriticalKpiRead]] = defaultdict(list)
    for d in defs:
        latest_map_all = repo.list_latest_value_per_system_for_definition(
            tenant_id,
            d.id,
            system_ids,
        )
        for sid, (val, _) in latest_map_all.items():
            st = kpi_value_status(
                val,
                d.recommended_direction,
                d.alert_threshold_high,
                d.alert_threshold_low,
            )
            if st == "red":
                critical_by_system[sid].append(
                    AiSystemCriticalKpiRead(
                        kpi_key=d.key,
                        name=d.name,
                        value=val,
                        unit=d.unit,
                    ),
                )

    for sid, rows in critical_by_system.items():
        if not rows:
            continue
        name, rl, _crit = id_to_meta[sid]
        per_system_critical.append(
            AiSystemCriticalRowRead(
                ai_system_id=sid,
                ai_system_name=name,
                risk_level=rl,
                critical_kpis=rows,
            ),
        )

    per_system_critical.sort(key=lambda r: (-len(r.critical_kpis), r.ai_system_name))

    return AiKpiSummaryResponse(
        per_kpi=per_kpi,
        per_system_critical=per_system_critical,
        high_risk_system_count=len(system_ids),
    )


def build_board_report_kpi_briefs(
    session: Session,
    tenant_id: str,
) -> tuple[list[BoardReportKpiSystemRowBrief], list[BoardReportKpiPortfolioRowBrief]]:
    """Kompakte KPI-Daten für LLM-Input (nur High-/Unacceptable-Risk)."""
    repo = AiKpiRepository(session)
    systems = repo.list_high_risk_system_ids(tenant_id)
    system_ids = [s[0] for s in systems]
    id_to_name = {s[0]: s[1] for s in systems}
    id_to_rl = {s[0]: s[2] for s in systems}

    defs = repo.list_definitions()
    systems_brief: list[BoardReportKpiSystemRowBrief] = []

    for sid in system_ids:
        kpis: list[BoardReportSystemKpiValueBrief] = []
        for d in defs:
            latest_map = repo.list_latest_value_per_system_for_definition(
                tenant_id,
                d.id,
                [sid],
            )
            prev_map = repo.list_second_latest_value_per_system(tenant_id, d.id, [sid])
            if sid not in latest_map:
                continue
            val, _ps = latest_map[sid]
            prev_v = prev_map.get(sid)
            tr = numeric_trend(prev_v, val)
            kpis.append(
                BoardReportSystemKpiValueBrief(
                    kpi_key=d.key,
                    name=d.name,
                    unit=d.unit,
                    latest_value=val,
                    trend=tr,
                ),
            )
        if kpis:
            systems_brief.append(
                BoardReportKpiSystemRowBrief(
                    ai_system_id=sid,
                    ai_system_name=id_to_name.get(sid, sid),
                    risk_level=id_to_rl.get(sid, ""),
                    kpis=kpis,
                ),
            )

    summary = build_ai_kpi_summary(session, tenant_id)
    portfolio = [
        BoardReportKpiPortfolioRowBrief(
            kpi_key=p.kpi_key,
            name=p.name,
            unit=p.unit,
            avg_high_risk_latest=p.avg_latest,
            trend_vs_prior_period=p.trend,
            systems_with_data=p.systems_with_data,
        )
        for p in summary.per_kpi
    ]
    return systems_brief, portfolio
