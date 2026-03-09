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
    created_at_utc: datetime


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
