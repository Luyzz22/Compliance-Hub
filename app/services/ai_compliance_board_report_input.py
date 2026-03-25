"""Assembler: Board-Report-Rohdaten aus Cross-Regulation + KI-Inventar (ohne LLM)."""

from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from app.ai_compliance_board_report_models import (
    AiComplianceBoardReportInput,
    AIInventoryBrief,
    FrameworkCoverageSnapshot,
    GapSnapshotBrief,
)
from app.feature_flags import FeatureFlag, is_feature_enabled
from app.repositories.ai_systems import AISystemRepository
from app.services.ai_kpi_service import build_board_report_kpi_briefs
from app.services.cross_regulation import build_cross_regulation_summary
from app.services.cross_regulation_gaps import compute_cross_regulation_gaps

_CRIT_ORDER = {"high": 0, "medium": 1, "low": 2}
_FW_RISK = {
    "eu_ai_act": 0,
    "nis2": 1,
    "iso_42001": 2,
    "iso_27001": 3,
    "dsgvo": 4,
    "iso_27701": 5,
}


def effective_focus_keys_for_board_report(
    *,
    focus_framework_keys: list[str] | None,
    include_ai_act_only: bool,
) -> list[str] | None:
    if include_ai_act_only:
        return ["eu_ai_act"]
    if focus_framework_keys:
        cleaned = [str(k).strip() for k in focus_framework_keys if str(k).strip()]
        return cleaned or None
    return None


def _gap_sort_key(g: GapSnapshotBrief) -> tuple[int, int, str]:
    c = _CRIT_ORDER.get(g.criticality.lower(), 99)
    fw = _FW_RISK.get(g.framework_key, 50)
    return (c, fw, g.code)


def build_ai_inventory_brief(ai_repo: AISystemRepository, tenant_id: str) -> AIInventoryBrief:
    raw = ai_repo.compliance_summary_for_tenant(tenant_id)
    by_risk = raw.get("by_risk_level") or []
    by_cat = raw.get("by_ai_act_category") or []
    by_crit = raw.get("by_criticality") or []
    high_risk = 0
    for row in by_risk:
        rl = str(row.get("risk_level", "")).lower()
        if rl in ("high", "unacceptable"):
            high_risk += int(row.get("count") or 0)
    high_crit = 0
    for row in by_crit:
        c = str(row.get("criticality", "")).lower()
        if c in ("high", "very_high"):
            high_crit += int(row.get("count") or 0)
    risk_rows_out: list[dict[str, int | str]] = []
    for x in by_risk:
        risk_rows_out.append(
            {"risk_level": str(x.get("risk_level", "")), "count": int(x.get("count") or 0)},
        )
    cat_rows_out: list[dict[str, int | str]] = []
    for x in by_cat:
        cat_rows_out.append(
            {
                "ai_act_category": str(x.get("ai_act_category", "")),
                "count": int(x.get("count") or 0),
            },
        )
    return AIInventoryBrief(
        total_systems=int(raw.get("total_systems") or 0),
        high_risk_ai_systems=high_risk,
        by_risk_level=risk_rows_out,
        by_ai_act_category=cat_rows_out,
        high_criticality_systems=high_crit,
    )


def assemble_ai_compliance_board_report_input(
    session: Session,
    tenant_id: str,
    *,
    audience_type: Literal["board", "management", "advisor_client"],
    language: str,
    focus_framework_keys: list[str] | None,
    include_ai_act_only: bool,
    ai_repo: AISystemRepository,
) -> AiComplianceBoardReportInput:
    eff = effective_focus_keys_for_board_report(
        focus_framework_keys=focus_framework_keys,
        include_ai_act_only=include_ai_act_only,
    )
    summary = build_cross_regulation_summary(session, tenant_id)
    coverage_rows = summary.frameworks
    if eff:
        allow = set(eff)
        coverage_rows = [f for f in coverage_rows if f.framework_key in allow]

    coverage = [
        FrameworkCoverageSnapshot(
            framework_key=f.framework_key,
            name=f.name,
            coverage_percent=f.coverage_percent,
            total_requirements=f.total_requirements,
            covered_requirements=f.covered_requirements,
            gap_count=f.gap_count,
            partial_count=f.partial_count,
            planned_only_count=f.planned_only_count,
        )
        for f in coverage_rows
    ]

    gaps_payload = compute_cross_regulation_gaps(session, tenant_id, focus_framework_keys=eff)
    briefs: list[GapSnapshotBrief] = []
    for g in gaps_payload.gaps:
        briefs.append(
            GapSnapshotBrief(
                requirement_id=g.requirement_id,
                framework_key=g.framework_key,
                code=g.code,
                title=g.title,
                criticality=g.criticality,
                requirement_type=g.requirement_type,
                coverage_status=g.coverage_status,
                linked_control_count=len(g.linked_controls),
            )
        )
    briefs.sort(key=_gap_sort_key)
    top_gaps = briefs[:10]

    inv = build_ai_inventory_brief(ai_repo, tenant_id)

    if is_feature_enabled(FeatureFlag.ai_kpi_kri, tenant_id, session=session):
        hr_kpis, port_kpis = build_board_report_kpi_briefs(session, tenant_id)
    else:
        hr_kpis, port_kpis = [], []

    return AiComplianceBoardReportInput(
        tenant_id=tenant_id,
        audience_type=audience_type,
        language=language,
        coverage=coverage,
        top_gaps=top_gaps,
        gap_assist_hints=[],
        ai_inventory=inv,
        trend_note="Keine historische Trendzeitreihe in dieser Version hinterlegt.",
        high_risk_kpi_summaries=hr_kpis,
        kpi_portfolio_aggregates=port_kpis,
    )
