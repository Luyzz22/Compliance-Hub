"""
Golden OAMI + event_subtype scenarios: index math, DE explain drivers, LLM JSON parse.

Fixtures: ``tests/fixtures/oami-subtype-explain/scenario_*.json`` (fixed ``now`` in tests).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.advisor_governance_maturity_brief_models import (
    AdvisorGovernanceMaturityBrief,
    advisor_brief_focus_marker_de,
    advisor_brief_portfolio_tooltip_de,
)
from app.governance_maturity_summary_models import (
    GovernanceMaturityActivitySlice,
    GovernanceMaturityOperationalMonitoringSlice,
    GovernanceMaturityOverallAssessment,
    GovernanceMaturityReadinessSlice,
    GovernanceMaturitySummary,
)
from app.operational_monitoring_models import OamiComponentsOut, SystemMonitoringIndexOut
from app.readiness_score_models import (
    ReadinessDimensionOut,
    ReadinessScoreDimensions,
    ReadinessScoreResponse,
)
from app.services.oami_explanation import explain_system_oami_de, oami_operational_hint_de
from app.services.operational_monitoring_index import _components_from_agg, _level_from_index
from app.services.readiness_explain_structured import parse_and_validate_readiness_explain_response

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "oami-subtype-explain"
_FIXED_NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)

_SCENARIO_FILES = (
    "scenario_s1_safety_heavy.json",
    "scenario_s2_availability_heavy.json",
    "scenario_s3_benign_low.json",
)


def _load_scenario(filename: str) -> dict:
    return json.loads((_FIXTURES / filename).read_text(encoding="utf-8"))


def _agg_for_components(scenario: dict) -> dict[str, object]:
    agg = dict(scenario["oami_aggregate"])
    age_days = int(agg.pop("last_event_age_days"))
    agg["last_occurred_at"] = _FIXED_NOW - timedelta(days=age_days)
    return agg


def _snapshot_for_scenario(scenario: dict) -> ReadinessScoreResponse:
    block = scenario["readiness_explain_llm_json"]["readiness_explanation"]
    dim = ReadinessDimensionOut
    d = ReadinessScoreDimensions(
        setup=dim(normalized=0.5, score_0_100=50),
        coverage=dim(normalized=0.5, score_0_100=50),
        kpi=dim(normalized=0.5, score_0_100=50),
        gaps=dim(normalized=0.5, score_0_100=50),
        reporting=dim(normalized=0.5, score_0_100=50),
    )
    return ReadinessScoreResponse(
        tenant_id=f"golden-oami-subtype-{scenario['id'].lower()}",
        score=int(block["score"]),
        level=block["level"],  # type: ignore[arg-type]
        interpretation="Fixture-Snapshot.",
        dimensions=d,
    )


def _system_index_out(
    scenario: dict,
    score: int,
    level: str,
    comp: OamiComponentsOut,
) -> SystemMonitoringIndexOut:
    raw = scenario["oami_aggregate"]
    agg = _agg_for_components(scenario)
    inc = dict(raw["incident_count_by_subtype"])
    msub = dict(raw["metric_breach_count_by_subtype"])
    safety = int(inc.get("safety_violation", 0)) + int(inc.get("bias_discrimination_incident", 0))
    avail = int(inc.get("availability_incident", 0))
    return SystemMonitoringIndexOut(
        ai_system_id="golden-subtype",
        tenant_id="t-fixture",
        window_days=int(scenario.get("window_days", 90)),
        operational_monitoring_index=score,
        level=level,  # type: ignore[arg-type]
        has_data=True,
        last_event_at=agg["last_occurred_at"],  # type: ignore[arg-type]
        incident_count=int(raw["incident_count"]),
        high_severity_incident_count=int(raw["incident_high"]),
        incident_count_by_subtype=inc,
        metric_breach_count_by_subtype=msub,
        safety_related_incident_count=safety,
        oami_operational_hint_de=oami_operational_hint_de(
            safety_incidents=safety,
            availability_incidents=avail,
        ),
        metric_threshold_breach_count=int(raw["breach_count"]),
        distinct_active_days=int(raw["distinct_days"]),
        components=comp,
    )


@pytest.mark.parametrize("filename", _SCENARIO_FILES)
def test_subtype_scenario_oami_index_and_level_match_fixture(filename: str) -> None:
    scenario = _load_scenario(filename)
    agg = _agg_for_components(scenario)
    comp, score, _ = _components_from_agg(agg, now=_FIXED_NOW, window_days=90)
    exp = scenario["expected"]
    assert score == exp["operational_monitoring_index"]
    assert _level_from_index(score) == exp["level"]


@pytest.mark.parametrize("filename", _SCENARIO_FILES)
def test_subtype_scenario_explain_drivers_contain_keywords(filename: str) -> None:
    scenario = _load_scenario(filename)
    agg = _agg_for_components(scenario)
    comp, score, _ = _components_from_agg(agg, now=_FIXED_NOW, window_days=90)
    level = _level_from_index(score)
    idx = _system_index_out(scenario, score, level, comp)
    explain = explain_system_oami_de(idx)
    joined = " ".join(explain.drivers_de).lower()
    for needle in scenario["assert_explain_drivers_contain"]:
        assert needle.lower() in joined, f"missing driver hint {needle!r} in {filename}"


@pytest.mark.parametrize("filename", _SCENARIO_FILES)
def test_subtype_scenario_readiness_llm_json_parses_with_enrichment(filename: str) -> None:
    scenario = _load_scenario(filename)
    exp = scenario["expected"]
    envelope = scenario["readiness_explain_llm_json"]
    raw = json.dumps(envelope, ensure_ascii=False)
    snap = _snapshot_for_scenario(scenario)
    enrichment = scenario.get("oami_enrichment")
    out = parse_and_validate_readiness_explain_response(
        raw,
        snapshot=snap,
        oami_index=exp["operational_monitoring_index"],
        oami_level=exp["level"],
        has_oami_context=True,
        provider="golden_subtype_fixture",
        model_id="scenario",
        oami_operational_enrichment=enrichment,
    )
    assert out.operational_monitoring_explanation is not None
    oami = out.operational_monitoring_explanation
    assert oami.index == exp["operational_monitoring_index"]
    assert oami.level == exp["level"]
    for needle in scenario["assert_llm_oami_text_contains"]:
        hay = (
            oami.recent_incidents_summary
            + " ".join(oami.monitoring_gaps)
            + " ".join(oami.improvement_suggestions)
        )
        assert needle.lower() in hay.lower(), f"missing LLM block hint {needle!r} in {filename}"

    if enrichment:
        assert oami.safety_related_incidents_90d == enrichment.get("safety_related_incidents_90d")
        assert oami.availability_incidents_90d == enrichment.get("availability_incidents_90d")
        hint = enrichment.get("oami_subtype_hint_de")
        if hint is not None:
            assert oami.oami_subtype_hint_de == hint
        else:
            assert oami.oami_subtype_hint_de is None


@pytest.mark.parametrize(
    ("filename", "focus_substrs"),
    [
        (
            "scenario_s1_safety_heavy.json",
            ("sicherheit", "verfügbarkeit"),
        ),
        (
            "scenario_s2_availability_heavy.json",
            ("verfügbarkeit", "safety"),
        ),
    ],
)
def test_governance_maturity_fragment_maps_to_advisor_brief_tooltips(
    filename: str,
    focus_substrs: tuple[str, ...],
) -> None:
    """Board-style operational copy + Advisor focus areas carry subtype context."""
    scenario = _load_scenario(filename)
    fragment = scenario["governance_maturity_fragment"]
    exp = scenario["expected"]

    oa = GovernanceMaturityOverallAssessment(
        level=exp["level"],
        short_summary="Fixture",
        key_risks=[],
        key_strengths=[],
    )
    summary = GovernanceMaturitySummary(
        readiness=GovernanceMaturityReadinessSlice(score=50, level="managed", short_reason="r"),
        activity=GovernanceMaturityActivitySlice(index=50, level="medium", short_reason="a"),
        operational_monitoring=GovernanceMaturityOperationalMonitoringSlice(
            index=exp["operational_monitoring_index"],
            level=exp["level"],
            short_reason=fragment["operational_monitoring_short_reason_de"],
        ),
        overall_assessment=oa,
    )
    brief = AdvisorGovernanceMaturityBrief(
        governance_maturity_summary=summary,
        recommended_focus_areas=list(fragment["recommended_focus_areas"]),
    )
    focus_blob = " ".join(brief.recommended_focus_areas).lower()
    for s in focus_substrs:
        assert s.lower() in focus_blob
    assert (
        brief.governance_maturity_summary.operational_monitoring.short_reason
        == fragment["operational_monitoring_short_reason_de"]
    )
    marker = advisor_brief_focus_marker_de(brief)
    assert marker.startswith("Fokus:")
    tooltip = advisor_brief_portfolio_tooltip_de(brief).lower()
    for s in focus_substrs:
        assert s.lower() in tooltip
