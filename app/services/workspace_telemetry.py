"""Workspace-Nutzungstelemetrie (NIS2/ISO-tauglich, strukturiert, ohne PII).

Zentrale Hilfsfunktionen auf Basis von usage_events + log_usage_event.
"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy.orm import Session

from app.services import usage_event_logger

ActorTypeTelemetry = Literal["tenant", "advisor", "system", "unknown"]


def actor_type_for_request_path(path: str) -> ActorTypeTelemetry:
    """Ableitung aus URL-Pfad (keine PII)."""
    p = path.split("?", 1)[0]
    if p.startswith("/api/v1/advisors/"):
        return "advisor"
    return "tenant"


def build_workspace_event_payload(
    *,
    workspace_mode: str,
    actor_type: str,
    result: str | None = None,
    feature_name: str | None = None,
    route: str | None = None,
    method: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Minimales, stabiles JSON-Schema für Workspace-Events (ohne Payloads/PII)."""
    data: dict[str, Any] = {
        "workspace_mode": workspace_mode,
        "actor_type": actor_type,
    }
    if result is not None:
        data["result"] = result
    if feature_name is not None:
        data["feature_name"] = feature_name
    if route is not None:
        data["route"] = route
    if method is not None:
        data["method"] = method
    if extra:
        for k, v in extra.items():
            if v is not None and k not in data:
                data[k] = v
    return data


def log_workspace_session_started(
    session: Session,
    tenant_id: str,
    *,
    workspace_mode: str,
    request_path: str,
    dedupe_same_type_hours: float | None = 24.0,
) -> None:
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        usage_event_logger.WORKSPACE_SESSION_STARTED,
        build_workspace_event_payload(
            workspace_mode=workspace_mode,
            actor_type=actor_type_for_request_path(request_path),
            result="success",
        ),
        dedupe_same_type_hours=dedupe_same_type_hours,
    )


def log_workspace_feature_used(
    session: Session,
    tenant_id: str,
    *,
    workspace_mode: str,
    feature_name: str,
    request_path: str,
) -> None:
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        usage_event_logger.WORKSPACE_FEATURE_USED,
        build_workspace_event_payload(
            workspace_mode=workspace_mode,
            actor_type=actor_type_for_request_path(request_path),
            feature_name=feature_name,
            result="success",
        ),
    )


def log_workspace_mutation_blocked(
    session: Session,
    tenant_id: str,
    *,
    workspace_mode: str,
    http_method: str,
    route: str,
    request_path: str,
) -> None:
    usage_event_logger.log_usage_event(
        session,
        tenant_id,
        usage_event_logger.WORKSPACE_MUTATION_BLOCKED,
        build_workspace_event_payload(
            workspace_mode=workspace_mode,
            actor_type=actor_type_for_request_path(request_path),
            result="forbidden_demo_readonly",
            route=route,
            method=http_method.upper(),
        ),
    )
