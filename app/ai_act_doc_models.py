"""Pydantic-Modelle für EU-AI-Act-Dokumentationsbausteine (Annex IV / Art. 11 orientiert)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AIActDocSectionKey(StrEnum):
    RISK_MANAGEMENT = "RISK_MANAGEMENT"
    DATA_GOVERNANCE = "DATA_GOVERNANCE"
    MONITORING_LOGGING = "MONITORING_LOGGING"
    HUMAN_OVERSIGHT = "HUMAN_OVERSIGHT"
    TECHNICAL_ROBUSTNESS = "TECHNICAL_ROBUSTNESS"


class AIActDocContentSource(StrEnum):
    manual = "manual"
    ai_generated = "ai_generated"


class AIActDoc(BaseModel):
    id: str
    tenant_id: str
    ai_system_id: str
    section_key: AIActDocSectionKey
    title: str
    content_markdown: str
    version: int = Field(
        ge=0,
        description="0 = nicht persistierter KI-/UI-Entwurf, ab 1 gespeicherte Version",
    )
    content_source: AIActDocContentSource | None = None
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str


class AIActDocUpsertRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content_markdown: str = Field(default="", max_length=200_000)
    content_source: AIActDocContentSource | None = None


class AIActDocListItem(BaseModel):
    """Eine Sektion inkl. UI-Status-Hinweis."""

    section_key: AIActDocSectionKey
    default_title: str
    doc: AIActDoc | None = None
    status: str = Field(
        description="empty | saved — Entwürfe ohne Persistenz nur im Client",
    )


class AIActDocListResponse(BaseModel):
    ai_system_id: str
    items: list[AIActDocListItem]
