"""OAMI Subtype-Gewichtung und erklärende Texte."""

from __future__ import annotations

from datetime import UTC, datetime

from app.advisor_governance_maturity_brief_models import (
    AdvisorGovernanceMaturityBrief,
    merge_recommended_focus_areas_runtime_safety,
)
from app.governance_maturity_summary_models import (
    GovernanceMaturityActivitySlice,
    GovernanceMaturityOperationalMonitoringSlice,
    GovernanceMaturityOverallAssessment,
    GovernanceMaturityReadinessSlice,
    GovernanceMaturitySummary,
)
from app.operational_monitoring_models import OamiComponentsOut, SystemMonitoringIndexOut
from app.services.oami_explanation import explain_system_oami_de, oami_operational_hint_de
from app.services.operational_monitoring_index import _components_from_agg


def _minimal_summary() -> GovernanceMaturitySummary:
    oa = GovernanceMaturityOverallAssessment(
        level="medium",
        short_summary="x",
        key_risks=[],
        key_strengths=[],
    )
    return GovernanceMaturitySummary(
        readiness=GovernanceMaturityReadinessSlice(score=50, level="managed", short_reason="r"),
        activity=GovernanceMaturityActivitySlice(index=50, level="medium", short_reason="a"),
        operational_monitoring=GovernanceMaturityOperationalMonitoringSlice(
            index=50,
            level="medium",
            short_reason="o",
        ),
        overall_assessment=oa,
    )


def test_oami_weighted_incidents_safety_lowers_score_vs_availability() -> None:
    now = datetime.now(UTC)
    wd = 90
    avail_sum = 3 * 1.0 * 0.065
    safe_sum = 3 * 1.5 * 0.065
    agg_a = {
        "event_count": 20,
        "last_occurred_at": now,
        "distinct_days": 10,
        "incident_high": 0,
        "breach_count": 0,
        "incident_count": 3,
        "incident_count_by_subtype": {"availability_incident": 3},
        "metric_breach_count_by_subtype": {},
        "incident_weighted_penalty_sum": avail_sum,
        "weighted_breach_units": 0.0,
    }
    agg_s = {
        **agg_a,
        "incident_count_by_subtype": {"safety_violation": 3},
        "incident_weighted_penalty_sum": safe_sum,
    }
    _, score_a, _ = _components_from_agg(agg_a, now=now, window_days=wd)
    _, score_s, _ = _components_from_agg(agg_s, now=now, window_days=wd)
    assert score_a > score_s


def test_oami_weighted_metric_breach_drift_hurts_more_than_performance() -> None:
    now = datetime.now(UTC)
    wd = 90
    scale = max(3.0, (wd / 30.0) * 5.0)
    perf_units = 3 * 1.0
    drift_units = 3 * 1.2
    agg_p = {
        "event_count": 15,
        "last_occurred_at": now,
        "distinct_days": 8,
        "incident_high": 0,
        "breach_count": 3,
        "incident_count": 0,
        "incident_count_by_subtype": {},
        "metric_breach_count_by_subtype": {"performance_degradation": 3},
        "incident_weighted_penalty_sum": 0.0,
        "weighted_breach_units": perf_units,
    }
    agg_d = {
        **agg_p,
        "metric_breach_count_by_subtype": {"drift_high": 3},
        "weighted_breach_units": drift_units,
    }
    _, score_p, _ = _components_from_agg(agg_p, now=now, window_days=wd)
    _, score_d, _ = _components_from_agg(agg_d, now=now, window_days=wd)
    assert score_p > score_d
    assert drift_units / scale > perf_units / scale


def test_explain_system_mentions_multiple_safety_subtypes() -> None:
    idx = SystemMonitoringIndexOut(
        ai_system_id="s1",
        tenant_id="t1",
        window_days=90,
        operational_monitoring_index=55,
        level="medium",
        has_data=True,
        last_event_at=datetime.now(UTC),
        incident_count=2,
        high_severity_incident_count=0,
        incident_count_by_subtype={"safety_violation": 2},
        metric_breach_count_by_subtype={},
        safety_related_incident_count=2,
        oami_operational_hint_de=None,
        metric_threshold_breach_count=0,
        distinct_active_days=5,
        components=OamiComponentsOut(
            freshness=0.8,
            activity_days=0.5,
            incident_stability=0.5,
            metric_stability=0.9,
        ),
    )
    out = explain_system_oami_de(idx)
    joined = " ".join(out.drivers_de)
    assert "Mehrere sicherheitsrelevante" in joined
    assert "safety_violation" in joined


def test_explain_system_mentions_drift_subtypes_when_repeated() -> None:
    idx = SystemMonitoringIndexOut(
        ai_system_id="s1",
        tenant_id="t1",
        window_days=90,
        operational_monitoring_index=50,
        level="medium",
        has_data=True,
        last_event_at=datetime.now(UTC),
        incident_count=0,
        high_severity_incident_count=0,
        incident_count_by_subtype={},
        metric_breach_count_by_subtype={"drift_high": 2},
        safety_related_incident_count=0,
        oami_operational_hint_de=None,
        metric_threshold_breach_count=2,
        distinct_active_days=5,
        components=OamiComponentsOut(
            freshness=0.8,
            activity_days=0.5,
            incident_stability=0.9,
            metric_stability=0.4,
        ),
    )
    out = explain_system_oami_de(idx)
    assert any("drift_high" in d.lower() for d in out.drivers_de)


def test_oami_operational_hint_safety_thresholds() -> None:
    assert oami_operational_hint_de(safety_incidents=0, availability_incidents=0) is None
    assert oami_operational_hint_de(safety_incidents=1, availability_incidents=0) is not None
    h2 = oami_operational_hint_de(safety_incidents=2, availability_incidents=0)
    assert h2 is not None
    assert "Mehrere" in h2


def test_merge_advisor_brief_adds_runtime_safety_focus() -> None:
    brief = AdvisorGovernanceMaturityBrief(
        governance_maturity_summary=_minimal_summary(),
        recommended_focus_areas=["Anderes Thema"],
    )
    merged = merge_recommended_focus_areas_runtime_safety(brief, 1)
    assert merged is not None
    assert len(merged.recommended_focus_areas) >= 2
    assert "Sicherheitsrelevante AI-Laufzeitvorfälle" in merged.recommended_focus_areas[0]


def test_merge_advisor_brief_idempotent_when_already_safety_focus() -> None:
    brief = AdvisorGovernanceMaturityBrief(
        governance_maturity_summary=_minimal_summary(),
        recommended_focus_areas=["Sicherheitsrelevante Registerpflege"],
    )
    merged = merge_recommended_focus_areas_runtime_safety(brief, 2)
    assert merged.recommended_focus_areas == brief.recommended_focus_areas
