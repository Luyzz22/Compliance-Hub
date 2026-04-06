from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditLog(BaseModel):
    id: int
    tenant_id: str
    actor: str
    action: str
    entity_type: str
    entity_id: str
    before: str | None = None
    after: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    previous_hash: str | None = None
    entry_hash: str | None = None
    created_at_utc: datetime
    actor_role: str | None = None
    outcome: str | None = None
    correlation_id: str | None = None
    metadata_json: str | None = None


class AuditEventBase(BaseModel):
    tenant_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor_type: str
    actor_id: str | None = None
    entity_type: str
    entity_id: str
    action: str
    metadata: dict[str, Any] | None = None


class AuditEvent(AuditEventBase):
    id: str
