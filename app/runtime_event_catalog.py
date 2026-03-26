"""Kanonische Werte für AI-Runtime-Event-Ingest (Validierung, Normalisierung)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from app.operational_monitoring_models import RuntimeEventIn

# event_subtype: optional DB column on AiRuntimeEventTable (nullable VARCHAR(64)).
# Future: whitelist / ingest validation for analytics (e.g. sap_ai_core_alert, drift_high,
# safety_violation). OAMI scoring today uses event_type + severity only; subtype is metadata.

# event_type (kleingeschrieben persistiert)
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

_SOURCE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_TECH_KEY_PATTERN = re.compile(r"^[a-zA-Z0-9_.:\-]{1,128}$")

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

    return ValidatedRuntimeFields(src, et, sev, mk, ic), None
