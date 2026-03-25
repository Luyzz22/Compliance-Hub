"""Unit: Readiness-Score-Mathematik und Randfälle."""

from __future__ import annotations

import pytest

from app.services.readiness_score_service import (
    ReadinessRawSignals,
    aggregate_weighted_score,
    build_interpretation,
    dimensions_from_signals,
)


def test_aggregate_weights_sum_to_one() -> None:
    s = ReadinessRawSignals(1, 1, 1, 1, 1)
    assert aggregate_weighted_score(s) == pytest.approx(1.0)

    s2 = ReadinessRawSignals(0, 0, 0, 0, 0)
    assert aggregate_weighted_score(s2) == pytest.approx(0.0)


def test_aggregate_partial_signal() -> None:
    s = ReadinessRawSignals(setup=1, coverage=0, kpi=0, gaps=0, reporting=0)
    # 20% * 1 + rest 0
    assert aggregate_weighted_score(s) == pytest.approx(0.2)


def test_build_interpretation_contains_score_and_level() -> None:
    s = ReadinessRawSignals(0.5, 0.5, 0.2, 0.5, 0.5)
    dims = dimensions_from_signals(s)
    text = build_interpretation(52, "managed", dims)
    assert "52/100" in text
    assert "Managed" in text


def test_dimensions_score_0_100_rounding() -> None:
    s = ReadinessRawSignals(0.333, 0.666, 1, 0, 0.5)
    d = dimensions_from_signals(s)
    assert d.setup.score_0_100 == 33
    assert d.coverage.score_0_100 == 67
