"""Unit-Tests: KPI-Trend- und Schwellenlogik."""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.ai_kpi_analytics import (
    kpi_value_status,
    numeric_trend,
    trend_from_series,
)


def test_numeric_trend_up_down_flat() -> None:
    assert numeric_trend(10.0, 12.0) == "up"
    assert numeric_trend(10.0, 8.0) == "down"
    assert numeric_trend(10.0, 10.005) == "flat"
    assert numeric_trend(None, 5.0) == "flat"


def test_trend_from_series_requires_two_points() -> None:
    t0 = datetime(2025, 1, 1, tzinfo=UTC)
    assert trend_from_series([(t0, 1.0)]) == "flat"
    t1 = datetime(2025, 4, 1, tzinfo=UTC)
    assert trend_from_series([(t0, 1.0), (t1, 3.0)]) == "up"


def test_kpi_value_status_down_direction() -> None:
    assert kpi_value_status(1.0, "down", 2.0, None) == "ok"
    assert kpi_value_status(3.0, "down", 2.0, None) == "red"


def test_kpi_value_status_up_direction() -> None:
    assert kpi_value_status(80.0, "up", None, 50.0) == "ok"
    assert kpi_value_status(40.0, "up", None, 50.0) == "red"
