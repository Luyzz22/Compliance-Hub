"""Board-What-if: hypothetische NIS2-/Readiness-Änderungen ohne DB-Schreibzugriff."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select

from app.ai_governance_models import (
    WhatIfBoardKpiType,
    WhatIfKpiAdjustment,
    WhatIfScenarioInput,
    WhatIfScenarioResult,
)
from app.config.nis2_kritis_board_alert_thresholds import DEFAULT_NIS2_KRITIS_THRESHOLD_CONFIG
from app.models_db import AISystemTable, Nis2KritisKpiDB
from app.nis2_kritis_models import Nis2KritisKpiType
from app.repositories.ai_systems import AISystemRepository
from app.repositories.classifications import ClassificationRepository
from app.repositories.compliance_gap import ComplianceGapRepository
from app.repositories.nis2_kritis_kpis import Nis2KritisKpiRepository
from app.repositories.violations import ViolationRepository
from app.services.ai_board_alerts import compute_board_alerts
from app.services.ai_governance_kpis import compute_ai_board_kpis
from app.services.compliance_dashboard import (
    compute_ai_compliance_overview,
    compute_compliance_dashboard,
)
from app.services.nis2_kritis_alert_signals import (
    Nis2KritisAlertSignals,
    build_nis2_kritis_alert_signals,
)

_cfg = DEFAULT_NIS2_KRITIS_THRESHOLD_CONFIG


def _load_kpi_value_map(
    session,
    tenant_id: str,
) -> dict[tuple[str, str], int]:
    stmt = select(
        Nis2KritisKpiDB.ai_system_id,
        Nis2KritisKpiDB.kpi_type,
        Nis2KritisKpiDB.value_percent,
    ).where(Nis2KritisKpiDB.tenant_id == tenant_id)
    out: dict[tuple[str, str], int] = {}
    for sid, kt, val in session.execute(stmt).all():
        out[(str(sid), str(kt))] = int(val)
    return out


def _apply_adjustments(
    base: dict[tuple[str, str], int],
    adjustments: Iterable[WhatIfKpiAdjustment],
) -> dict[tuple[str, str], int]:
    m = dict(base)
    for adj in adjustments:
        if adj.kpi_type == WhatIfBoardKpiType.EU_AI_ACT_CONTROL_FULFILLMENT:
            continue
        m[(adj.ai_system_id, adj.kpi_type.value)] = adj.target_value_percent
    return m


def _aggregate_from_map(
    tenant_system_ids: list[str],
    kpi_map: dict[tuple[str, str], int],
) -> tuple[float | None, float]:
    values = [v for (sid, _kt), v in kpi_map.items() if sid in tenant_system_ids]
    if not values:
        return None, 0.0
    mean = sum(values) / len(values)
    full = 0
    for sid in tenant_system_ids:
        keys = {kt for (s, kt) in kpi_map if s == sid}
        if keys >= {e.value for e in Nis2KritisKpiType}:
            full += 1
    ratio = full / len(tenant_system_ids) if tenant_system_ids else 0.0
    return mean, ratio


def _mean_by_nis2_type(
    tenant_system_ids: list[str],
    kpi_map: dict[tuple[str, str], int],
) -> dict[Nis2KritisKpiType, float | None]:
    out: dict[Nis2KritisKpiType, float | None] = {}
    for kt in Nis2KritisKpiType:
        vals = [kpi_map[(sid, kt.value)] for sid in tenant_system_ids if (sid, kt.value) in kpi_map]
        out[kt] = sum(vals) / len(vals) if vals else None
    return out


def _list_lowest_systems(
    tenant_system_ids: list[str],
    kpi_map: dict[tuple[str, str], int],
    kpi_type: Nis2KritisKpiType,
    *,
    limit: int,
) -> list[str]:
    pairs: list[tuple[str, int]] = []
    for sid in tenant_system_ids:
        key = (sid, kpi_type.value)
        if key in kpi_map:
            pairs.append((sid, kpi_map[key]))
    pairs.sort(key=lambda x: (x[1], x[0]))
    return [p[0] for p in pairs[:limit]]


def _focus_system_ids_low_ot(
    session,
    tenant_id: str,
    kpi_map: dict[tuple[str, str], int],
    *,
    threshold_percent: int,
    limit: int,
) -> tuple[int, list[str]]:
    stmt = select(AISystemTable).where(AISystemTable.tenant_id == tenant_id)
    systems = session.execute(stmt).scalars().all()
    focus_low: list[tuple[str, int]] = []
    count = 0
    kt = Nis2KritisKpiType.OT_IT_SEGREGATION.value
    for row in systems:
        is_focus = (
            row.risk_level == "high"
            or row.ai_act_category == "high_risk"
            or row.criticality in ("high", "very_high")
        )
        key = (row.id, kt)
        if key not in kpi_map:
            continue
        v = kpi_map[key]
        if is_focus and v < threshold_percent:
            count += 1
            focus_low.append((row.id, v))
    focus_low.sort(key=lambda x: (x[1], x[0]))
    return count, [x[0] for x in focus_low[:limit]]


def _signals_from_map(
    session,
    tenant_id: str,
    kpi_map: dict[tuple[str, str], int],
) -> Nis2KritisAlertSignals:
    sys_stmt = select(AISystemTable.id).where(AISystemTable.tenant_id == tenant_id)
    system_ids = [str(x) for x in session.execute(sys_stmt).scalars().all()]
    means = _mean_by_nis2_type(system_ids, kpi_map)
    thr = int(_cfg.ot_it_segmentation.focus_system_value_below_percent)
    ot_n, ot_ids = _focus_system_ids_low_ot(
        session,
        tenant_id,
        kpi_map,
        threshold_percent=thr,
        limit=3,
    )
    return Nis2KritisAlertSignals(
        incident_mean_percent=means[Nis2KritisKpiType.INCIDENT_RESPONSE_MATURITY],
        supplier_mean_percent=means[Nis2KritisKpiType.SUPPLIER_RISK_COVERAGE],
        ot_it_mean_percent=means[Nis2KritisKpiType.OT_IT_SEGREGATION],
        high_risk_focus_low_ot_it_count=ot_n,
        incident_worst_system_ids=tuple(
            _list_lowest_systems(
                system_ids,
                kpi_map,
                Nis2KritisKpiType.INCIDENT_RESPONSE_MATURITY,
                limit=3,
            ),
        ),
        supplier_worst_system_ids=tuple(
            _list_lowest_systems(
                system_ids,
                kpi_map,
                Nis2KritisKpiType.SUPPLIER_RISK_COVERAGE,
                limit=3,
            ),
        ),
        ot_it_worst_focus_system_ids=tuple(ot_ids),
    )


def _blend_readiness(
    overall: float,
    old_mean: float | None,
    new_mean: float | None,
    eu_act_delta: float,
) -> float:
    out = overall + eu_act_delta
    if old_mean is not None and new_mean is not None:
        out += 0.25 * ((new_mean - old_mean) / 100.0)
    return max(0.0, min(1.0, round(out, 4)))


def _eu_act_readiness_delta(
    adjustments: list[WhatIfKpiAdjustment],
    system_readiness: dict[str, float],
) -> float:
    delta = 0.0
    for adj in adjustments:
        if adj.kpi_type != WhatIfBoardKpiType.EU_AI_ACT_CONTROL_FULFILLMENT:
            continue
        base = system_readiness.get(adj.ai_system_id)
        if base is None:
            continue
        target = adj.target_value_percent / 100.0
        delta += 0.2 * (target - base)
    return delta


def _alert_signature(a) -> str:
    return f"{a.kpi_key}|{a.severity}"


def simulate_board_impact(
    scenario: WhatIfScenarioInput,
    tenant_id: str,
    *,
    session,
    ai_repo: AISystemRepository,
    cls_repo: ClassificationRepository,
    gap_repo: ComplianceGapRepository,
    violation_repo: ViolationRepository,
    nis2_repo: Nis2KritisKpiRepository,
) -> WhatIfScenarioResult:
    base_map = _load_kpi_value_map(session, tenant_id)
    sim_map = _apply_adjustments(base_map, scenario.kpi_adjustments)

    orig_overview = compute_ai_compliance_overview(
        tenant_id=tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    sys_stmt = select(AISystemTable.id).where(AISystemTable.tenant_id == tenant_id)
    system_ids = [str(x) for x in session.execute(sys_stmt).scalars().all()]
    orig_mean, orig_cov = _aggregate_from_map(system_ids, base_map)
    sim_mean, sim_cov = _aggregate_from_map(system_ids, sim_map)

    dashboard = compute_compliance_dashboard(
        tenant_id=tenant_id,
        ai_repo=ai_repo,
        cls_repo=cls_repo,
        gap_repo=gap_repo,
    )
    system_readiness = {s.ai_system_id: s.readiness_score for s in dashboard.systems}
    eu_delta = _eu_act_readiness_delta(scenario.kpi_adjustments, system_readiness)

    sim_readiness = _blend_readiness(
        orig_overview.overall_readiness,
        orig_mean,
        sim_mean,
        eu_delta,
    )
    sim_overview = orig_overview.model_copy(
        update={
            "overall_readiness": sim_readiness,
            "nis2_kritis_kpi_mean_percent": round(sim_mean, 2) if sim_mean is not None else None,
            "nis2_kritis_systems_full_coverage_ratio": round(sim_cov, 4),
        },
    )

    board_orig = compute_ai_board_kpis(
        tenant_id=tenant_id,
        ai_system_repository=ai_repo,
        violation_repository=violation_repo,
        nis2_kritis_kpi_repository=nis2_repo,
    )
    board_sim = board_orig.model_copy(
        update={
            "nis2_kritis_kpi_mean_percent": round(sim_mean, 2) if sim_mean is not None else None,
            "nis2_kritis_systems_full_coverage_ratio": round(sim_cov, 4),
        },
    )

    ot_thr = int(_cfg.ot_it_segmentation.focus_system_value_below_percent)
    alerts_orig = compute_board_alerts(
        tenant_id=tenant_id,
        board_kpis=board_orig,
        compliance_overview=orig_overview,
        nis2_kritis_signals=build_nis2_kritis_alert_signals(
            tenant_id,
            nis2_repo,
            ot_it_threshold_percent=ot_thr,
        ),
    )
    alerts_sim = compute_board_alerts(
        tenant_id=tenant_id,
        board_kpis=board_sim,
        compliance_overview=sim_overview,
        nis2_kritis_signals=_signals_from_map(session, tenant_id, sim_map),
    )

    sig_o = {_alert_signature(a) for a in alerts_orig}
    sig_s = {_alert_signature(a) for a in alerts_sim}

    return WhatIfScenarioResult(
        original_readiness=orig_overview.overall_readiness,
        simulated_readiness=sim_readiness,
        original_board_kpis=board_orig,
        simulated_board_kpis=board_sim,
        original_compliance_overview=orig_overview,
        simulated_compliance_overview=sim_overview,
        original_alerts_count=len(alerts_orig),
        simulated_alerts_count=len(alerts_sim),
        alert_signatures_new=sorted(sig_s - sig_o),
        alert_signatures_resolved=sorted(sig_o - sig_s),
    )
