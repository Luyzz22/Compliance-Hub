"""Trend- und Schwellenlogik für AI-KPIs (ohne HTTP)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

Trend = Literal["up", "down", "flat"]
Status = Literal["ok", "red"]


def numeric_trend(previous: float | None, latest: float) -> Trend:
    """Vergleich letzter vs. vorletzter Wert; Toleranz relativ 1 % oder absolut 0,01."""
    if previous is None:
        return "flat"
    tol = max(0.01, abs(previous) * 0.01)
    if latest > previous + tol:
        return "up"
    if latest < previous - tol:
        return "down"
    return "flat"


def kpi_value_status(
    value: float,
    recommended_direction: str,
    alert_threshold_high: float | None,
    alert_threshold_low: float | None,
) -> Status:
    """Einfache Ampel: bei „down = gut“ rot wenn über alert_threshold_high."""
    d = recommended_direction.lower()
    if d == "down":
        if alert_threshold_high is not None and value > alert_threshold_high:
            return "red"
    elif d == "up":
        if alert_threshold_low is not None and value < alert_threshold_low:
            return "red"
    return "ok"


def trend_from_series(values_asc_by_period: list[tuple[datetime, float]]) -> Trend:
    """values sortiert nach period_start aufsteigend."""
    if len(values_asc_by_period) < 2:
        return "flat"
    prev_v = values_asc_by_period[-2][1]
    last_v = values_asc_by_period[-1][1]
    return numeric_trend(prev_v, last_v)


def mean_or_none(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None
