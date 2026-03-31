"""Governance maturity Board summary: golden LLM JSON, snapshot alignment, conservative overall."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.governance_maturity_models import (
    GovernanceActivityBlock,
    GovernanceMaturityResponse,
    GovernanceReadinessBlock,
    OperationalAiMonitoringBlock,
)
from app.services.governance_maturity_summary_parse import (
    conservative_overall_level_from_snapshot,
    parse_governance_maturity_board_summary,
    parse_governance_maturity_summary,
)

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "governance_maturity_summary_golden"


def _snap_basic_low() -> GovernanceMaturityResponse:
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
    return GovernanceMaturityResponse(
        tenant_id="golden-basic",
        computed_at=now,
        readiness=GovernanceReadinessBlock(
            score=38,
            level="basic",
            interpretation="Strukturell noch im Aufbau.",
        ),
        governance_activity=GovernanceActivityBlock(
            index=35,
            level="low",
            window_days=90,
            last_computed_at=now,
            components=None,
        ),
        operational_ai_monitoring=OperationalAiMonitoringBlock(
            status="active",
            index=32,
            level="low",
            window_days=90,
            message_de="Kurz OAMI.",
            drivers_de=[],
        ),
    )


def _snap_embedded_high() -> GovernanceMaturityResponse:
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
    return GovernanceMaturityResponse(
        tenant_id="golden-embedded",
        computed_at=now,
        readiness=GovernanceReadinessBlock(
            score=88,
            level="embedded",
            interpretation="Hohe strukturelle Reife.",
        ),
        governance_activity=GovernanceActivityBlock(
            index=72,
            level="high",
            window_days=90,
            last_computed_at=now,
            components=None,
        ),
        operational_ai_monitoring=OperationalAiMonitoringBlock(
            status="active",
            index=78,
            level="high",
            window_days=90,
            message_de="OAMI stark.",
            drivers_de=["a"],
        ),
    )


def test_conservative_overall_level_min_of_pillars() -> None:
    s = _snap_basic_low()
    assert conservative_overall_level_from_snapshot(s) == "low"
    s2 = _snap_embedded_high()
    assert conservative_overall_level_from_snapshot(s2) == "high"


def test_parse_governance_maturity_summary_alias() -> None:
    raw = (_FIXTURES / "response_basic_low.json").read_text(encoding="utf-8")
    a = parse_governance_maturity_summary(raw, _snap_basic_low())
    b = parse_governance_maturity_board_summary(raw, _snap_basic_low())
    assert a.summary.model_dump() == b.summary.model_dump()
    assert (
        a.executive_overview_governance_maturity_de == b.executive_overview_governance_maturity_de
    )


def test_golden_basic_low_aligns_scores_and_levels_to_snapshot() -> None:
    raw = (_FIXTURES / "response_basic_low.json").read_text(encoding="utf-8")
    snap = _snap_basic_low()
    out = parse_governance_maturity_board_summary(raw, snap)
    assert out.parse_ok is True
    assert out.used_llm_paragraph is True
    assert out.summary.readiness.score == 38
    assert out.summary.readiness.level == "basic"
    assert out.summary.activity.index == 35
    assert out.summary.activity.level == "low"
    assert out.summary.operational_monitoring.index == 32
    assert out.summary.operational_monitoring.level == "low"
    assert out.summary.overall_assessment.level == "low"
    assert "Aufsicht" in out.executive_overview_governance_maturity_de


def test_golden_embedded_high_overwrites_wrong_llm_levels() -> None:
    raw = (_FIXTURES / "response_embedded_high.json").read_text(encoding="utf-8")
    snap = _snap_embedded_high()
    out = parse_governance_maturity_board_summary(raw, snap)
    assert out.summary.readiness.score == 88
    assert out.summary.readiness.level == "embedded"
    assert out.summary.activity.level == "high"
    assert out.summary.operational_monitoring.level == "high"
    assert out.summary.overall_assessment.level == "high"
    assert "reifes Steuerungsbild" in out.executive_overview_governance_maturity_de


def test_parse_fallback_on_invalid_json() -> None:
    snap = _snap_basic_low()
    out = parse_governance_maturity_board_summary("not json {{{", snap)
    assert out.parse_ok is False
    assert out.summary.readiness.level == "basic"
    assert out.used_llm_paragraph is False


def test_oami_not_configured_null_index_level() -> None:
    now = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
    snap = GovernanceMaturityResponse(
        tenant_id="t-oami-off",
        computed_at=now,
        readiness=GovernanceReadinessBlock(score=60, level="managed", interpretation="OK."),
        governance_activity=GovernanceActivityBlock(
            index=50,
            level="medium",
            window_days=90,
            last_computed_at=now,
        ),
        operational_ai_monitoring=OperationalAiMonitoringBlock(
            status="not_configured",
            index=None,
            level=None,
            window_days=90,
            message_de="Keine Daten.",
        ),
    )
    raw = (_FIXTURES / "response_basic_low.json").read_text(encoding="utf-8")
    out = parse_governance_maturity_board_summary(raw, snap)
    assert out.summary.operational_monitoring.index is None
    assert out.summary.operational_monitoring.level is None
    assert conservative_overall_level_from_snapshot(snap) == "medium"


def test_board_report_prompt_contains_governance_blocks() -> None:
    from app.ai_compliance_board_report_models import AiComplianceBoardReportInput
    from app.governance_maturity_summary_models import (
        GovernanceMaturityActivitySlice,
        GovernanceMaturityOperationalMonitoringSlice,
        GovernanceMaturityOverallAssessment,
        GovernanceMaturityReadinessSlice,
        GovernanceMaturitySummary,
    )
    from app.services.ai_compliance_board_report_llm import build_board_report_user_prompt

    gm = GovernanceMaturitySummary(
        readiness=GovernanceMaturityReadinessSlice(
            score=50,
            level="managed",
            short_reason="x",
        ),
        activity=GovernanceMaturityActivitySlice(index=50, level="medium", short_reason="y"),
        operational_monitoring=GovernanceMaturityOperationalMonitoringSlice(
            index=50,
            level="medium",
            short_reason="z",
        ),
        overall_assessment=GovernanceMaturityOverallAssessment(
            level="medium",
            short_summary="s",
            key_risks=[],
            key_strengths=[],
        ),
    )
    para = (
        "Dies ist ein ausreichend langer Pflichtabsatz für den Vorstand mit genügend "
        "Zeicheninhalt zur Verankerung."
    )
    inp = AiComplianceBoardReportInput(
        tenant_id="t",
        audience_type="board",
        governance_maturity_summary=gm,
        governance_maturity_executive_paragraph_de=para,
    )
    p = build_board_report_user_prompt(inp)
    assert "Governance-Reife (Pflicht)" in p
    assert "Governance-Reife (Readiness, GAI, OAMI)" in p
    assert para in p
    assert "governance_maturity_summary" in p
