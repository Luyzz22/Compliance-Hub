"""Unit-Tests: OAMI Incident-Subtype-Profil für Board-Report."""

from __future__ import annotations

from app.operational_monitoring_models import TenantOperationalMonitoringIndexOut
from app.services.oami_incident_subtype_profile_board import (
    build_oami_incident_subtype_profile_for_board,
)


def _tenant(
    *,
    has_data: bool,
    by_sub: dict[str, int],
    level: str = "medium",
    index: int = 60,
    hint: str | None = None,
) -> TenantOperationalMonitoringIndexOut:
    sv = int(by_sub.get("safety_violation", 0))
    av = int(by_sub.get("availability_incident", 0))
    return TenantOperationalMonitoringIndexOut(
        tenant_id="t-test",
        window_days=90,
        operational_monitoring_index=index,
        level=level,  # type: ignore[arg-type]
        systems_scored=2 if has_data else 0,
        has_any_runtime_data=has_data,
        components=None,
        explanation=None,
        runtime_incident_by_subtype=dict(by_sub),
        safety_related_runtime_incident_count=sv,
        availability_runtime_incident_count=av,
        oami_operational_hint_de=hint,
    )


def test_profile_none_without_runtime_data() -> None:
    to = _tenant(has_data=False, by_sub={})
    assert build_oami_incident_subtype_profile_for_board(to) is None


def test_profile_none_without_incidents_or_hint() -> None:
    to = _tenant(has_data=True, by_sub={})
    assert build_oami_incident_subtype_profile_for_board(to) is None


def test_profile_safety_dominant_shares_and_narrative() -> None:
    to = _tenant(
        has_data=True,
        by_sub={"safety_violation": 3, "availability_incident": 1},
        level="medium",
        index=65,
    )
    p = build_oami_incident_subtype_profile_for_board(to)
    assert p is not None
    assert p.incident_weighted_share_safety > p.incident_weighted_share_availability
    assert p.incident_count_by_category.safety == 3
    assert p.incident_count_by_category.availability == 1
    narr = p.oami_subtype_narrative_de.lower()
    assert "sicherheit" in narr or "sicherheits" in narr


def test_profile_availability_dominant() -> None:
    to = _tenant(
        has_data=True,
        by_sub={"availability_incident": 9},
        level="medium",
        index=60,
    )
    p = build_oami_incident_subtype_profile_for_board(to)
    assert p is not None
    assert p.incident_weighted_share_availability == 1.0
    assert "Verfügbarkeit" in p.oami_subtype_narrative_de


def test_profile_low_other_incidents_uses_benign_narrative() -> None:
    to = _tenant(
        has_data=True,
        by_sub={"other_incident": 2},
        level="low",
        index=37,
    )
    p = build_oami_incident_subtype_profile_for_board(to)
    assert p is not None
    narr = p.oami_subtype_narrative_de
    assert "niedrig" in narr.lower() or "Stufe" in narr


def test_shares_sum_to_one() -> None:
    to = _tenant(
        has_data=True,
        by_sub={"safety_violation": 1, "availability_incident": 1, "other_incident": 1},
    )
    p = build_oami_incident_subtype_profile_for_board(to)
    assert p is not None
    s = (
        p.incident_weighted_share_safety
        + p.incident_weighted_share_availability
        + p.incident_weighted_share_other
    )
    assert abs(s - 1.0) < 0.02
