"""event_subtype taxonomy, SAP-Code-Mapping und Soft-Normalisierung."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.operational_monitoring_models import RuntimeEventIn
from app.runtime_event_catalog import (
    resolve_event_subtype,
    validate_runtime_event_fields,
)


def _ev(**kwargs: object) -> RuntimeEventIn:
    base = {
        "source_event_id": "e1",
        "source": "sap_ai_core",
        "event_type": "incident",
        "occurred_at": datetime(2025, 1, 1, tzinfo=UTC),
    }
    base.update(kwargs)
    return RuntimeEventIn.model_validate(base)


def test_valid_explicit_subtype() -> None:
    ev = _ev(event_subtype="safety_violation")
    vf, err = validate_runtime_event_fields(ev)
    assert err is None and vf is not None
    vf2, w = resolve_event_subtype(ev, vf)
    assert vf2.event_subtype == "safety_violation"
    assert w == []


def test_unknown_subtype_coerced_to_other_incident() -> None:
    ev = _ev(event_subtype="totally_unknown_xyz")
    vf, err = validate_runtime_event_fields(ev)
    assert err is None and vf is not None
    vf2, w = resolve_event_subtype(ev, vf)
    assert vf2.event_subtype == "other_incident"
    assert "subtype_unknown_coerced_to_other" in w


def test_sap_incident_code_maps_subtype() -> None:
    ev = _ev(incident_code="SAFETY_VIOLATION")
    vf, err = validate_runtime_event_fields(ev)
    assert err is None and vf is not None
    vf2, w = resolve_event_subtype(ev, vf)
    assert vf2.event_subtype == "safety_violation"
    assert w == []


def test_sap_code_type_mismatch_no_subtype_when_incompatible() -> None:
    """DRIFT_HIGH mappt auf breach; deklariertes event_type incident → kein Subtype aus Code."""
    ev = _ev(event_type="incident", incident_code="DRIFT_HIGH")
    vf, err = validate_runtime_event_fields(ev)
    assert err is None and vf is not None
    vf2, w = resolve_event_subtype(ev, vf)
    assert vf2.event_subtype is None
    assert "provider_code_event_type_mismatch" in w


def test_metric_breach_explicit_performance_degradation() -> None:
    ev = _ev(
        event_type="metric_threshold_breach",
        event_subtype="performance_degradation",
        metric_key="latency_p95",
    )
    vf, err = validate_runtime_event_fields(ev)
    assert err is None and vf is not None
    vf2, w = resolve_event_subtype(ev, vf)
    assert vf2.event_subtype == "performance_degradation"
    assert w == []


def test_heartbeat_ignores_subtype() -> None:
    ev = _ev(event_type="heartbeat", event_subtype="safety_violation")
    vf, err = validate_runtime_event_fields(ev)
    assert err is None and vf is not None
    vf2, w = resolve_event_subtype(ev, vf)
    assert vf2.event_subtype is None
    assert "subtype_ignored_non_incident_event_type" in w


def test_explicit_subtype_wins_over_provider_code() -> None:
    ev = _ev(
        event_subtype="availability_incident",
        incident_code="SAFETY_VIOLATION",
    )
    vf, err = validate_runtime_event_fields(ev)
    assert err is None and vf is not None
    vf2, w = resolve_event_subtype(ev, vf)
    assert vf2.event_subtype == "availability_incident"


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("MODEL_ROLLOUT", "model_rollout"),
        ("DEPLOYMENT_ROLLBACK", "model_rollback"),
    ],
)
def test_deployment_sap_codes(code: str, expected: str) -> None:
    ev = _ev(event_type="deployment_change", incident_code=code)
    vf, err = validate_runtime_event_fields(ev)
    assert err is None and vf is not None
    vf2, _w = resolve_event_subtype(ev, vf)
    assert vf2.event_subtype == expected
