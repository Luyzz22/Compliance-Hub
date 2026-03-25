"""Workspace-Nutzungstelemetrie (NIS2/ISO, SIEM-tauglich, ohne PII).

Zentrale API: ``emit_workspace_event`` → ``usage_events`` (+ optional strukturiertes App-Log).
Alle Emissionen sind **best-effort** (Fehler brechen den Request nicht).

``extra`` ist **ausschließlich nach Whitelist** (Schlüssel + Typ/Wert-Regeln).
Kein Freitext, keine PII.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.services import usage_event_logger

logger = logging.getLogger(__name__)

ActorTypeTelemetry = Literal["tenant", "advisor", "system", "unknown"]

# Nur explizit erlaubte Kontext-Schlüssel (Referenz-IDs / Enums, keine Personen-/Freitextfelder)
_EXTRA_ALLOWED_KEYS = frozenset({
    "action_id",
    "ai_system_id",
    "audit_record_id",
    "classification_id",
    "control_id",
    "evidence_id",
    "export_job_id",
    "framework_key",
    "job_id",
    "report_id",
    "requirement_id",
    "surface",
    "template_key",
})

# Erlaubte Zeichen in String-Werten: technische IDs und Keys, kein Freitext
_EXTRA_STR_VALUE_PATTERN = re.compile(r"^[a-zA-Z0-9_.:/\-]{1,128}$")


def _env_truthy(key: str) -> bool:
    raw = os.getenv(key, "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def route_template_from_request(request: Any) -> str:
    """OpenAPI-Pfad-Template (zyklusfrei; dupliziert Logik aus demo_tenant_guard)."""
    route = request.scope.get("route")
    if route is not None:
        path = getattr(route, "path", None)
        if path:
            return str(path)
    return str(request.url.path)


def actor_type_for_request_path(path: str) -> ActorTypeTelemetry:
    """Ableitung aus URL-Pfad (keine PII)."""
    p = path.split("?", 1)[0]
    if p.startswith("/api/v1/advisors/"):
        return "advisor"
    return "tenant"


def _sanitize_extra(extra: dict[str, Any] | None) -> dict[str, Any]:
    """Whitelist-only: unbekannte Schlüssel und ungültige Werte werden verworfen."""
    if not extra:
        return {}
    out: dict[str, Any] = {}
    for k, v in extra.items():
        if not isinstance(k, str) or not k.strip():
            continue
        kn = k.strip()
        if kn not in _EXTRA_ALLOWED_KEYS:
            continue
        if isinstance(v, bool):
            out[kn] = v
        elif isinstance(v, int) and -1_000_000_000 <= v <= 1_000_000_000:
            out[kn] = v
        elif isinstance(v, str) and _EXTRA_STR_VALUE_PATTERN.fullmatch(v):
            out[kn] = v
    return out


def build_workspace_event_body(
    *,
    event_type: str,
    tenant_id: str,
    workspace_mode: str,
    actor_type: str,
    feature_name: str | None = None,
    result: str | None = None,
    route: str | None = None,
    method: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Gemeinsames JSON-Schema für Export (eine Zeile payload_json + Spalten in usage_events).

    Immer gesetzt: event_type, tenant_id, workspace_mode, actor_type, timestamp (ISO-UTC).
    """
    ts = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    data: dict[str, Any] = {
        "event_type": event_type,
        "tenant_id": tenant_id,
        "workspace_mode": workspace_mode,
        "actor_type": actor_type,
        "timestamp": ts,
    }
    if result is not None:
        data["result"] = result
    if feature_name is not None:
        data["feature_name"] = feature_name
    if route is not None:
        data["route"] = route
    if method is not None:
        data["method"] = str(method).upper()
    data.update(_sanitize_extra(extra))
    return data


def emit_workspace_event(
    session: Session,
    event_type: str,
    tenant_id: str,
    *,
    workspace_mode: str,
    actor_type: str,
    feature_name: str | None = None,
    result: str | None = None,
    route: str | None = None,
    method: str | None = None,
    extra: dict[str, Any] | None = None,
    dedupe_same_type_hours: float | None = None,
) -> None:
    """
    Zentrale Workspace-Telemetrie (synchron, ORM-Session).

    - Wirft **nie** nach außen: Fehler nur intern geloggt (wie ``log_usage_event``).
    """
    body = build_workspace_event_body(
        event_type=event_type,
        tenant_id=tenant_id,
        workspace_mode=workspace_mode,
        actor_type=actor_type,
        feature_name=feature_name,
        result=result,
        route=route,
        method=method,
        extra=extra,
    )
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        event_type,
        body,
        dedupe_same_type_hours=dedupe_same_type_hours,
    )
    if _env_truthy("COMPLIANCEHUB_WORKSPACE_TELEMETRY_STRUCTURED_LOG"):
        try:
            line = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
            logger.info("workspace_telemetry %s", line)
        except Exception:
            logger.exception("workspace_telemetry_structured_log_failed")


def log_workspace_session_started(
    session: Session,
    tenant_id: str,
    *,
    workspace_mode: str,
    request_path: str,
    dedupe_same_type_hours: float | None = 24.0,
) -> None:
    emit_workspace_event(
        session,
        usage_event_logger.WORKSPACE_SESSION_STARTED,
        tenant_id,
        workspace_mode=workspace_mode,
        actor_type=actor_type_for_request_path(request_path),
        result="success",
        dedupe_same_type_hours=dedupe_same_type_hours,
    )


def log_workspace_feature_used(
    session: Session,
    tenant_id: str,
    *,
    workspace_mode: str,
    feature_name: str,
    request_path: str,
    route: str | None = None,
    method: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    emit_workspace_event(
        session,
        usage_event_logger.WORKSPACE_FEATURE_USED,
        tenant_id,
        workspace_mode=workspace_mode,
        actor_type=actor_type_for_request_path(request_path),
        feature_name=feature_name,
        result="success",
        route=route,
        method=method,
        extra=extra,
    )


def log_workspace_mutation_blocked(
    session: Session,
    tenant_id: str,
    *,
    workspace_mode: str,
    http_method: str,
    route: str,
    request_path: str,
    feature_name: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    emit_workspace_event(
        session,
        usage_event_logger.WORKSPACE_MUTATION_BLOCKED,
        tenant_id,
        workspace_mode=workspace_mode,
        actor_type=actor_type_for_request_path(request_path),
        result="forbidden_demo_readonly",
        route=route,
        method=http_method,
        feature_name=feature_name,
        extra=extra,
    )
