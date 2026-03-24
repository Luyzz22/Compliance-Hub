"""Tenant-weite NIS2-/KRITIS-KPI-Drilldowns (Histogramm, Worst-Offenders)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from app.datetime_compat import UTC
from app.nis2_kritis_models import (
    Nis2KritisKpiCriticalSystemEntry,
    Nis2KritisKpiDrilldown,
    Nis2KritisKpiHistogramBucket,
    Nis2KritisKpiType,
    Nis2KritisKpiTypeDrilldown,
)
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository

# Frontend-Pfad zur EU-AI-Act-/Gap-Ansicht (NIS2-KPI-Pflege)
NIS2_KRITIS_DETAIL_HREF = "/tenant/eu-ai-act"

_BUCKET_BOUNDS = (
    (0, 25),
    (25, 50),
    (50, 75),
    (75, 101),
)


def _bucket_index(value_percent: int) -> int:
    for i, (_lo, hi_ex) in enumerate(_BUCKET_BOUNDS):
        if value_percent < hi_ex:
            return i
    return len(_BUCKET_BOUNDS) - 1


def build_nis2_kritis_kpi_drilldown(
    tenant_id: str,
    nis2_repo: Nis2KritisKpiRepository,
    *,
    top_n: int = 5,
) -> Nis2KritisKpiDrilldown:
    rows = nis2_repo.list_kpis_with_system_for_tenant(tenant_id)
    by_type: dict[Nis2KritisKpiType, list[tuple[int, str, str, str]]] = defaultdict(list)
    for kpi, name, bu in rows:
        by_type[kpi.kpi_type].append((kpi.value_percent, kpi.ai_system_id, name, bu))

    type_drilldowns: list[Nis2KritisKpiTypeDrilldown] = []
    for kt in Nis2KritisKpiType:
        entries = by_type.get(kt, [])
        hist_counts = [0, 0, 0, 0]
        for vp, *_rest in entries:
            hist_counts[_bucket_index(vp)] += 1
        histogram = [
            Nis2KritisKpiHistogramBucket(
                range_min_inclusive=lo,
                range_max_exclusive=hi_ex,
                count=hist_counts[i],
            )
            for i, (lo, hi_ex) in enumerate(_BUCKET_BOUNDS)
        ]
        sorted_entries = sorted(entries, key=lambda t: t[0])
        worst = sorted_entries[:top_n]
        critical = [
            Nis2KritisKpiCriticalSystemEntry(
                ai_system_id=sid,
                name=n,
                business_unit=bu,
                kpi_type=kt,
                value_percent=vp,
                detail_href=NIS2_KRITIS_DETAIL_HREF,
            )
            for vp, sid, n, bu in worst
        ]
        type_drilldowns.append(
            Nis2KritisKpiTypeDrilldown(
                kpi_type=kt,
                histogram=histogram,
                critical_systems=critical,
            )
        )

    return Nis2KritisKpiDrilldown(
        tenant_id=tenant_id,
        generated_at=datetime.now(UTC),
        top_n=top_n,
        by_kpi_type=type_drilldowns,
    )
