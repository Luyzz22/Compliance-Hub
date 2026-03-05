from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
