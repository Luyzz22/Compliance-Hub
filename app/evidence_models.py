from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EvidenceFile(BaseModel):
    id: str
    tenant_id: str
    ai_system_id: str | None = None
    audit_record_id: str | None = None
    action_id: str | None = None
    filename_original: str
    content_type: str
    size_bytes: int = Field(..., ge=0)
    uploaded_by: str
    norm_framework: str | None = None
    norm_reference: str | None = None
    created_at: datetime
    updated_at: datetime


class EvidenceFileListResponse(BaseModel):
    items: list[EvidenceFile]
