"""Konservative OAMI-Gewichte pro ``event_subtype`` (v1, erklärbar, ohne UI-Zahlen)."""

from __future__ import annotations

from typing import Final

# Relativ zu Neutral 1.0; keine exponenziellen Formeln.
_INCIDENT_WEIGHTS: Final[dict[str, float]] = {
    "safety_violation": 1.5,
    "sap_alert_incident": 1.0,
    "availability_incident": 1.0,
    "other_incident": 0.8,
}

_METRIC_BREACH_WEIGHTS: Final[dict[str, float]] = {
    "drift_high": 1.2,
    "performance_degradation": 1.0,
    "other_metric_breach": 0.8,
}

# Pro Vorfall: high/critical stärker gewichtet als niedrigere Schwere (unabhängig vom Subtype).
_COEF_INCIDENT_HIGH: Final[float] = 0.20
_COEF_INCIDENT_OTHER_SEV: Final[float] = 0.065
_SEV_HI: Final[frozenset[str]] = frozenset({"high", "critical"})


def incident_subtype_oami_weight(subtype: str | None) -> float:
    """Gewicht für einen Incident (ohne Subtype: neutral 1.0)."""
    if not subtype or not str(subtype).strip():
        return 1.0
    k = str(subtype).strip().lower()
    if k.startswith("other_"):
        return 0.8
    return float(_INCIDENT_WEIGHTS.get(k, 1.0))


def metric_breach_subtype_oami_weight(subtype: str | None) -> float:
    """Gewicht für eine Metrik-Schwellenverletzung."""
    if not subtype or not str(subtype).strip():
        return 1.0
    k = str(subtype).strip().lower()
    if k.startswith("other_"):
        return 0.8
    return float(_METRIC_BREACH_WEIGHTS.get(k, 1.0))


def incident_weighted_penalty_contribution(*, subtype: str | None, severity: str | None) -> float:
    """Summand für OAMI-Incident-Teilscore (vor Sättigung)."""
    w = incident_subtype_oami_weight(subtype)
    sev = (severity or "").strip().lower()
    coef = _COEF_INCIDENT_HIGH if sev in _SEV_HI else _COEF_INCIDENT_OTHER_SEV
    return w * coef
