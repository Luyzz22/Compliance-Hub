"""Regelbasierte Berater-Priorität und Szenario-Zuordnung (A–D)."""

from __future__ import annotations

import pytest

from app.services.advisor_portfolio_priority import (
    advisor_portfolio_priority_sort_key,
    apply_regulatory_priority_adjustment,
    compute_advisor_priority_bucket,
    compute_incident_burden_level,
    derive_primary_focus_tag_de,
    effective_readiness_level,
    infer_maturity_scenario_hint,
    normalize_nis2_entity_category,
    regulatory_priority_bump_applies,
)


@pytest.mark.parametrize(
    ("summary_level", "eu", "expected"),
    [
        ("managed", 0.4, "managed"),
        ("basic", 0.8, "basic"),
    ],
)
def test_effective_readiness_level_prefers_api_summary(
    summary_level: str,
    eu: float,
    expected: str,
) -> None:
    from app.readiness_score_models import ReadinessScoreSummary

    rs = ReadinessScoreSummary(score=50, level=summary_level)  # type: ignore[arg-type]
    assert effective_readiness_level(rs, eu) == expected


def test_effective_readiness_level_proxy_from_eu_when_no_summary() -> None:
    assert effective_readiness_level(None, 0.4) == "basic"
    assert effective_readiness_level(None, 0.6) == "managed"
    assert effective_readiness_level(None, 0.9) == "embedded"


@pytest.mark.parametrize(
    ("r", "g", "o", "hint"),
    [
        ("basic", "low", "low", "a"),
        ("managed", "high", "low", "b"),
        ("embedded", "medium", "medium", "c"),
        ("embedded", "high", "high", "d"),
        ("managed", "medium", "low", None),
    ],
)
def test_infer_maturity_scenario_hint(
    r: str,
    g: str,
    o: str | None,
    hint: str | None,
) -> None:
    assert infer_maturity_scenario_hint(r, g, o) == hint


def test_infer_maturity_scenario_hint_missing_oami_treated_as_low_for_a() -> None:
    assert infer_maturity_scenario_hint("basic", "low", None) == "a"


@pytest.mark.parametrize(
    ("r", "g", "o", "scenario", "bucket"),
    [
        ("basic", "low", "low", "a", "high"),
        ("managed", "high", "low", "b", "high"),
        ("embedded", "high", "high", "d", "low"),
        ("embedded", "medium", "medium", "c", "medium"),
        ("basic", "high", "high", None, "medium"),
    ],
)
def test_compute_priority_bucket(
    r: str,
    g: str | None,
    o: str | None,
    scenario: str | None,
    bucket: str,
) -> None:
    assert (
        compute_advisor_priority_bucket(
            r,
            g,
            o,
            scenario,  # type: ignore[arg-type]
        )
        == bucket
    )


def test_high_priority_without_scenario_when_managed_and_low_oami() -> None:
    assert compute_advisor_priority_bucket("managed", "medium", "low", None) == "high"


def test_sort_key_order() -> None:
    assert advisor_portfolio_priority_sort_key("high") < advisor_portfolio_priority_sort_key("low")


def test_normalize_nis2_entity_category_maps_legacy_in_scope() -> None:
    assert normalize_nis2_entity_category(None) == "none"
    assert normalize_nis2_entity_category("out_of_scope") == "none"
    assert normalize_nis2_entity_category("essential_entity") == "essential_entity"
    assert normalize_nis2_entity_category("in_scope") == "important_entity"


def test_compute_incident_burden_level_buckets() -> None:
    assert compute_incident_burden_level(0, 0) == "low"
    assert compute_incident_burden_level(1, 0) == "medium"
    assert compute_incident_burden_level(5, 0) == "high"
    assert compute_incident_burden_level(2, 2) == "high"


def test_regulatory_bump_requires_maturity_stress() -> None:
    assert regulatory_priority_bump_applies(
        nis2_category="essential_entity",
        kritis_sector_key=None,
        recent_incidents_90d=False,
        incident_burden="low",
        readiness_level="managed",
        oami_level="low",
    )
    assert not regulatory_priority_bump_applies(
        nis2_category="essential_entity",
        kritis_sector_key=None,
        recent_incidents_90d=False,
        incident_burden="low",
        readiness_level="embedded",
        oami_level="high",
    )


def test_regulatory_bump_incidents_medium_burden() -> None:
    assert regulatory_priority_bump_applies(
        nis2_category="none",
        kritis_sector_key=None,
        recent_incidents_90d=True,
        incident_burden="medium",
        readiness_level="basic",
        oami_level="high",
    )


def test_apply_regulatory_priority_adjustment_appends_suffix() -> None:
    adj, expl = apply_regulatory_priority_adjustment(
        "low",
        "Geringe Dringlichkeit.",
        readiness_level="managed",
        oami_level="low",
        nis2_category="essential_entity",
        kritis_sector_key=None,
        recent_incidents_90d=False,
        incident_burden="low",
    )
    assert adj == "medium"
    assert "Regulatorischer Aufstock" in expl


def test_primary_focus_from_brief_text() -> None:
    from app.advisor_governance_maturity_brief_models import AdvisorGovernanceMaturityBrief
    from app.governance_maturity_summary_models import (
        GovernanceMaturityActivitySlice,
        GovernanceMaturityOperationalMonitoringSlice,
        GovernanceMaturityOverallAssessment,
        GovernanceMaturityReadinessSlice,
        GovernanceMaturitySummary,
    )

    gm = GovernanceMaturitySummary(
        readiness=GovernanceMaturityReadinessSlice(score=50, level="managed", short_reason="x"),
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
    brief = AdvisorGovernanceMaturityBrief(
        governance_maturity_summary=gm,
        recommended_focus_areas=["OAMI niedrig – Monitoring ausbauen"],
        suggested_next_steps_window="nächste 90 Tage",
    )
    assert (
        derive_primary_focus_tag_de(
            brief,
            readiness_level="embedded",
            gai_level="high",
            oami_level="high",
        )
        == "Monitoring"
    )


def test_portfolio_filter_scenario_a_tenants() -> None:
    """Filterlogik: nur Mandanten mit Szenario A (wie im Portfolio-Frontend)."""
    rows = [
        {"tenant_id": "t1", "maturity_scenario_hint": "a", "advisor_priority": "high"},
        {"tenant_id": "t2", "maturity_scenario_hint": "b", "advisor_priority": "high"},
        {"tenant_id": "t3", "maturity_scenario_hint": None, "advisor_priority": "medium"},
    ]
    f = [r for r in rows if r["maturity_scenario_hint"] == "a"]
    assert [x["tenant_id"] for x in f] == ["t1"]


def test_portfolio_filter_high_priority() -> None:
    rows = [
        {"tenant_id": "t1", "advisor_priority": "high"},
        {"tenant_id": "t2", "advisor_priority": "low"},
    ]
    assert [r["tenant_id"] for r in rows if r["advisor_priority"] == "high"] == ["t1"]
