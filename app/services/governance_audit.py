"""Central helper for enterprise governance events in the GoBD-style audit_logs table."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from app.rbac.roles import EnterpriseRole
from app.repositories.audit_logs import AuditLogRepository
from app.services.audit_metadata_sanitize import metadata_json_safe


def correlation_id_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    return request.headers.get("x-correlation-id") or request.headers.get("x-request-id")


def actor_id_from_request(request: Request | None, fallback: str = "api_key_subject") -> str:
    if request is None:
        return fallback
    return (request.headers.get("x-actor-id") or "").strip() or fallback


def client_ip_from_request(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def user_agent_from_request(request: Request | None) -> str | None:
    if request is None:
        return None
    return request.headers.get("user-agent")


def record_governance_audit(
    audit_repo: AuditLogRepository,
    *,
    tenant_id: str,
    actor_id: str,
    actor_role: EnterpriseRole,
    action: str,
    entity_type: str,
    entity_id: str,
    outcome: str,
    before: str | None,
    after: str | None,
    correlation_id: str | None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    audit_repo.record_event(
        tenant_id=tenant_id,
        actor=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        ip_address=ip_address,
        user_agent=user_agent,
        actor_role=actor_role.value,
        outcome=outcome,
        correlation_id=correlation_id,
        metadata_json=metadata_json_safe(metadata),
    )
