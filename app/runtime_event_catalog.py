"""Kanonische Werte für AI-Runtime-Event-Ingest (Validierung, Normalisierung)."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Final

from app.operational_monitoring_models import RuntimeEventIn

# --- event_type (kleingeschrieben persistiert) ---
CANONICAL_EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "incident",
        "metric_threshold_breach",
        "deployment_change",
        "heartbeat",
        "metric_snapshot",
    },
)

CANONICAL_SEVERITIES: Final[frozenset[str]] = frozenset(
    {"info", "low", "medium", "high", "critical"},
)

CANONICAL_SOURCES: Final[frozenset[str]] = frozenset(
    {
        "sap_ai_core",
        "sap_btp_event_mesh",
        "manual_import",
        "other_provider",
        "synthetic_demo_seed",
    },
)

# --- event_subtype (v1, optional pro event_type) ---
# Generische Eimer bei unbekanntem Freitext (soft normalisieren, kein Reject).
EVENT_SUBTYPES_BY_TYPE: Final[dict[str, frozenset[str]]] = {
    "incident": frozenset(
        {
            "sap_alert_incident",
            "safety_violation",
            "availability_incident",
            "other_incident",
        },
    ),
    "metric_threshold_breach": frozenset(
        {
            "drift_high",
            "performance_degradation",
            "other_metric_breach",
        },
    ),
    "deployment_change": frozenset(
        {
            "model_rollout",
            "model_rollback",
            "other_deployment",
        },
    ),
    "heartbeat": frozenset(),
    "metric_snapshot": frozenset(),
}

OTHER_SUBTYPE_BY_TYPE: Final[dict[str, str]] = {
    "incident": "other_incident",
    "metric_threshold_breach": "other_metric_breach",
    "deployment_change": "other_deployment",
}

# SAP AI Core / ähnliche technische Codes (uppercase Schlüssel) → kanonisches (event_type, subtype).
# Neutral im Produkt: Zuordnung erfolgt hier zentral; APIs bleiben event_type + subtype.
SAP_AI_CORE_CODE_MAP: Final[dict[str, tuple[str, str]]] = {
    "SAFETY_VIOLATION": ("incident", "safety_violation"),
    "SERIOUS_INCIDENT": ("incident", "safety_violation"),
    "SAFETY_ALERT": ("incident", "safety_violation"),
    "AVAILABILITY_INCIDENT": ("incident", "availability_incident"),
    "SERVICE_DOWN": ("incident", "availability_incident"),
    "SAP_ALERT_INCIDENT": ("incident", "sap_alert_incident"),
    "AI_CORE_ALERT": ("incident", "sap_alert_incident"),
    "DRIFT_HIGH": ("metric_threshold_breach", "drift_high"),
    "MODEL_DRIFT": ("metric_threshold_breach", "drift_high"),
    "PERFORMANCE_DEGRADATION": ("metric_threshold_breach", "performance_degradation"),
    "LATENCY_SPIKE": ("metric_threshold_breach", "performance_degradation"),
    "MODEL_ROLLOUT": ("deployment_change", "model_rollout"),
    "DEPLOYMENT_ROLLOUT": ("deployment_change", "model_rollout"),
    "MODEL_ROLLBACK": ("deployment_change", "model_rollback"),
    "DEPLOYMENT_ROLLBACK": ("deployment_change", "model_rollback"),
}

_SOURCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_TECH_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_.:\-]{1,128}$")
_SUBTYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

_REJECTION_MESSAGES_EN: Final[dict[str, str]] = {
    "invalid_source": "Invalid or disallowed source identifier",
    "invalid_event_type": "event_type is not a known canonical type",
    "invalid_severity": "severity is not in the allowed set",
    "invalid_metric_key": "metric_key has invalid format (allowed: technical id pattern)",
    "invalid_incident_code": "incident_code has invalid format (allowed: technical id pattern)",
}


@dataclass(frozen=True)
class ValidatedRuntimeFields:
    source: str
    event_type: str
    severity: str | None
    metric_key: str | None
    incident_code: str | None
    event_subtype: str | None = None


def rejection_message_en(code: str) -> str:
    return _REJECTION_MESSAGES_EN.get(code, "Validation failed")


def validate_runtime_event_fields(
    ev: RuntimeEventIn,
) -> tuple[ValidatedRuntimeFields | None, str | None]:
    """
    Liefert (ValidatedRuntimeFields, None) oder (None, error_code).
    error_code: invalid_source | invalid_event_type | invalid_severity | ...
    """
    src = str(ev.source).strip().lower()[:64]
    if not src or (src not in CANONICAL_SOURCES and _SOURCE_PATTERN.fullmatch(src) is None):
        return None, "invalid_source"

    et = str(ev.event_type).strip().lower()[:64]
    if et not in CANONICAL_EVENT_TYPES:
        return None, "invalid_event_type"

    sev: str | None = None
    if ev.severity is not None and str(ev.severity).strip():
        sev = str(ev.severity).strip().lower()[:32]
        if sev not in CANONICAL_SEVERITIES:
            return None, "invalid_severity"

    mk: str | None = None
    if ev.metric_key is not None and str(ev.metric_key).strip():
        mk = str(ev.metric_key).strip()[:128]
        if _TECH_KEY_PATTERN.fullmatch(mk) is None:
            return None, "invalid_metric_key"

    ic: str | None = None
    if ev.incident_code is not None and str(ev.incident_code).strip():
        ic = str(ev.incident_code).strip()[:128]
        if _TECH_KEY_PATTERN.fullmatch(ic) is None:
            return None, "invalid_incident_code"

    return ValidatedRuntimeFields(src, et, sev, mk, ic, None), None


def _mapped_subtype_from_provider_code(vf: ValidatedRuntimeFields) -> tuple[str | None, str | None]:
    """Liefert (event_type_from_map, subtype) bei erkanntem Provider-``incident_code``."""
    if vf.source != "sap_ai_core" or not vf.incident_code:
        return None, None
    key = vf.incident_code.strip().upper()
    if key not in SAP_AI_CORE_CODE_MAP:
        return None, None
    et, st = SAP_AI_CORE_CODE_MAP[key]
    return et, st


def resolve_event_subtype(
    ev: RuntimeEventIn,
    vf: ValidatedRuntimeFields,
) -> tuple[ValidatedRuntimeFields, list[str]]:
    """
    Setzt ``event_subtype`` (oder ``None``). Unbekannte Werte werden auf ``other_*`` gemappt
    (soft). heartbeat/metric_snapshot: Subtype wird ignoriert.

    Rückgabe: (aktualisierte ValidatedRuntimeFields, Soft-Warn-Codes für Logging).
    """
    warnings: list[str] = []
    allowed = EVENT_SUBTYPES_BY_TYPE.get(vf.event_type, frozenset())
    other_bucket = OTHER_SUBTYPE_BY_TYPE.get(vf.event_type)

    if vf.event_type in ("heartbeat", "metric_snapshot"):
        raw = (ev.event_subtype or "").strip().lower() if ev.event_subtype else ""
        if raw:
            warnings.append("subtype_ignored_non_incident_event_type")
        return replace(vf, event_subtype=None), warnings

    explicit_raw = (ev.event_subtype or "").strip().lower()[:64] if ev.event_subtype else ""
    if explicit_raw and _SUBTYPE_PATTERN.fullmatch(explicit_raw) is None:
        warnings.append("subtype_invalid_chars_dropped")
        explicit_raw = ""

    map_et, map_st = _mapped_subtype_from_provider_code(vf)
    candidate: str | None = None
    if explicit_raw:
        candidate = explicit_raw
    elif map_st:
        if map_et is not None and map_et != vf.event_type:
            warnings.append("provider_code_event_type_mismatch")
        if map_st in allowed:
            candidate = map_st

    if not candidate:
        return replace(vf, event_subtype=None), warnings

    if candidate in allowed:
        return replace(vf, event_subtype=candidate), warnings

    if other_bucket is not None:
        warnings.append("subtype_unknown_coerced_to_other")
        return replace(vf, event_subtype=other_bucket), warnings

    warnings.append("subtype_dropped_no_bucket")
    return replace(vf, event_subtype=None), warnings
