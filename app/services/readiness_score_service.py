"""Berechnet den AI & Compliance Readiness Score aus vorhandenen Mandantensignalen."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.feature_flags import FeatureFlag, is_feature_enabled
from app.readiness_score_models import (
    ReadinessDimensionOut,
    ReadinessLevel,
    ReadinessScoreDimensions,
    ReadinessScoreResponse,
)
from app.repositories.ai_compliance_board_reports import AiComplianceBoardReportRepository
from app.repositories.ai_kpis import AiKpiRepository
from app.repositories.tenant_ai_governance_setup import TenantAIGovernanceSetupRepository
from app.services.cross_regulation import build_cross_regulation_summary
from app.services.cross_regulation_gaps import compute_cross_regulation_gaps
from app.services.setup_status import compute_tenant_setup_status
from app.services.tenant_ai_governance_setup import build_setup_response, normalize_payload

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Gewichtung (Summe = 1.0), angelehnt an Research/Monte-Carlo-Vorgabe
W_SETUP = 0.20
W_COVERAGE = 0.30
W_KPI = 0.20
W_GAPS = 0.20
W_REPORTING = 0.10

WIZARD_STEPS_TOTAL = 6
MIN_KPIS_PER_HIGH_RISK_SYSTEM = 2
CRITICAL_GAP_CRITICALITIES = frozenset({"high"})


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _to_display_score(n: float) -> int:
    return int(round(_clamp01(n) * 100.0))


def _level_from_score(score: int) -> ReadinessLevel:
    if score < 45:
        return "basic"
    if score < 70:
        return "managed"
    return "embedded"


@dataclass(frozen=True)
class ReadinessRawSignals:
    setup: float
    coverage: float
    kpi: float
    gaps: float
    reporting: float


def aggregate_weighted_score(signals: ReadinessRawSignals) -> float:
    """Gewichteter Gesamtscore 0–1 (vor Rundung auf 0–100)."""
    return _clamp01(
        W_SETUP * signals.setup
        + W_COVERAGE * signals.coverage
        + W_KPI * signals.kpi
        + W_GAPS * signals.gaps
        + W_REPORTING * signals.reporting,
    )


def dimensions_from_signals(signals: ReadinessRawSignals) -> ReadinessScoreDimensions:
    return ReadinessScoreDimensions(
        setup=ReadinessDimensionOut(
            normalized=signals.setup,
            score_0_100=_to_display_score(signals.setup),
        ),
        coverage=ReadinessDimensionOut(
            normalized=signals.coverage,
            score_0_100=_to_display_score(signals.coverage),
        ),
        kpi=ReadinessDimensionOut(
            normalized=signals.kpi,
            score_0_100=_to_display_score(signals.kpi),
        ),
        gaps=ReadinessDimensionOut(
            normalized=signals.gaps,
            score_0_100=_to_display_score(signals.gaps),
        ),
        reporting=ReadinessDimensionOut(
            normalized=signals.reporting,
            score_0_100=_to_display_score(signals.reporting),
        ),
    )


def build_interpretation(score: int, level: ReadinessLevel, dims: ReadinessScoreDimensions) -> str:
    """Statische Kurzinterpretation (deutsch), größte Hebel aus den schwächsten Dimensionen."""
    level_de = {"basic": "Basic", "managed": "Managed", "embedded": "Embedded"}.get(level, level)
    pairs = [
        ("Setup & Wizard", dims.setup.normalized),
        ("Framework-Coverage", dims.coverage.normalized),
        ("KPI-Abdeckung (High-Risk)", dims.kpi.normalized),
        ("Gap-Last (kritische Lücken)", dims.gaps.normalized),
        ("Report-Reife", dims.reporting.normalized),
    ]
    pairs.sort(key=lambda x: x[1])
    weak = [p[0] for p in pairs[:2] if p[1] < 0.85]
    weak_txt = " und ".join(weak) if weak else "Feintuning über alle Dimensionen"
    return (
        f"Ihr aktueller AI & Compliance Readiness Score liegt bei {score}/100 "
        f"(Level: {level_de}). Größte Hebel: {weak_txt}."
    )


def _setup_completion(session: Session, tenant_id: str) -> float:
    if is_feature_enabled(FeatureFlag.ai_governance_setup_wizard):
        try:
            raw = TenantAIGovernanceSetupRepository(session).get_payload(tenant_id)
            payload = normalize_payload(raw)
            ag = build_setup_response(session, tenant_id, payload)
            prog = {
                p
                for p in ag.progress_steps
                if isinstance(p, int) and 1 <= p <= WIZARD_STEPS_TOTAL
            }
            return len(prog) / float(WIZARD_STEPS_TOTAL)
        except Exception:
            logger.exception("readiness_setup_wizard_failed tenant=%s", tenant_id)
    guided = compute_tenant_setup_status(session, tenant_id)
    total = max(guided.total_steps, 1)
    return guided.completed_steps / float(total)


def _framework_coverage_and_gaps(
    session: Session,
    tenant_id: str,
    active_framework_keys: list[str],
) -> tuple[float, float]:
    """(coverage 0–1, gaps 0–1 inverted burden)."""
    if not is_feature_enabled(FeatureFlag.cross_regulation_dashboard):
        return 0.0, 1.0
    try:
        xsum = build_cross_regulation_summary(session, tenant_id)
        focus = [k for k in active_framework_keys if k and str(k).strip()]
        rows = (
            [f for f in xsum.frameworks if f.framework_key in focus]
            if focus
            else list(xsum.frameworks)
        )
        if not rows:
            return 0.0, 1.0
        cov = sum(f.coverage_percent for f in rows) / (100.0 * len(rows))
        cov = _clamp01(cov)
        total_reqs = sum(int(f.total_requirements) for f in rows)
        gaps_payload = compute_cross_regulation_gaps(
            session,
            tenant_id,
            focus_framework_keys=focus if focus else None,
        )
        crit_gaps = sum(
            1
            for g in gaps_payload.gaps
            if str(g.criticality).strip().lower() in CRITICAL_GAP_CRITICALITIES
        )
        if total_reqs <= 0:
            gap_score = 1.0
        else:
            burden = crit_gaps / float(total_reqs)
            gap_score = 1.0 - _clamp01(burden * 4.0)
        return cov, gap_score
    except Exception:
        logger.exception("readiness_cross_reg_failed tenant=%s", tenant_id)
        return 0.0, 1.0


def _kpi_readiness(session: Session, tenant_id: str) -> float:
    if not is_feature_enabled(FeatureFlag.ai_kpi_kri):
        return 0.0
    try:
        repo = AiKpiRepository(session)
        systems = repo.list_high_risk_system_ids(tenant_id)
        if not systems:
            return 1.0
        ok = 0
        for sid, _, _, _ in systems:
            vals = repo.list_values_for_system(tenant_id, sid)
            distinct_defs = {v.kpi_definition_id for v in vals}
            if len(distinct_defs) >= MIN_KPIS_PER_HIGH_RISK_SYSTEM:
                ok += 1
        return ok / float(len(systems))
    except Exception:
        logger.exception("readiness_kpi_failed tenant=%s", tenant_id)
        return 0.0


def _report_maturity(session: Session, tenant_id: str) -> float:
    if not is_feature_enabled(FeatureFlag.ai_compliance_board_report):
        return 0.0
    try:
        rows = AiComplianceBoardReportRepository(session).list_for_tenant(tenant_id, limit=200)
        n = len(rows)
        if n <= 0:
            return 0.0
        if n == 1:
            return 0.5
        return 1.0
    except Exception:
        logger.exception("readiness_reports_failed tenant=%s", tenant_id)
        return 0.0


def collect_raw_signals(session: Session, tenant_id: str) -> ReadinessRawSignals:
    setup = _setup_completion(session, tenant_id)
    active_fw: list[str] = []
    if is_feature_enabled(FeatureFlag.ai_governance_setup_wizard):
        try:
            raw = TenantAIGovernanceSetupRepository(session).get_payload(tenant_id)
            payload = normalize_payload(raw)
            active_fw = list(payload.get("active_frameworks") or [])
        except Exception:
            logger.exception("readiness_active_fw_failed tenant=%s", tenant_id)
    coverage, gaps = _framework_coverage_and_gaps(session, tenant_id, active_fw)
    kpi = _kpi_readiness(session, tenant_id)
    reporting = _report_maturity(session, tenant_id)
    return ReadinessRawSignals(
        setup=_clamp01(setup),
        coverage=_clamp01(coverage),
        kpi=_clamp01(kpi),
        gaps=_clamp01(gaps),
        reporting=_clamp01(reporting),
    )


def compute_readiness_score(session: Session, tenant_id: str) -> ReadinessScoreResponse:
    signals = collect_raw_signals(session, tenant_id)
    total01 = aggregate_weighted_score(signals)
    score = int(round(total01 * 100.0))
    score = max(0, min(100, score))
    level = _level_from_score(score)
    dims = dimensions_from_signals(signals)
    interpretation = build_interpretation(score, level, dims)
    return ReadinessScoreResponse(
        tenant_id=tenant_id,
        score=score,
        level=level,
        interpretation=interpretation,
        dimensions=dims,
    )
