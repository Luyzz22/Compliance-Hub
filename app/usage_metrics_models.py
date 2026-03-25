"""API-Modelle für Mandanten-Nutzungsmetriken (aus usage_events)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TenantUsageMetricsResponse(BaseModel):
    tenant_id: str
    last_active_at: datetime | None = Field(
        default=None,
        description="Zeitpunkt des letzten Nutzungsereignisses (UTC).",
    )
    board_views_last_30d: int = Field(ge=0)
    advisor_views_last_30d: int = Field(ge=0)
    evidence_uploads_last_30d: int = Field(ge=0)
    actions_created_last_30d: int = Field(ge=0)
    llm_calls_last_30d: int = Field(
        default=0,
        ge=0,
        description="Anzahl LLM-Router-Aufrufe (nur Metadaten geloggt), letzte 30 Tage.",
    )
    llm_legal_reasoning_calls_last_30d: int = Field(default=0, ge=0)
    llm_structured_output_calls_last_30d: int = Field(default=0, ge=0)
    llm_classification_calls_last_30d: int = Field(default=0, ge=0)
    llm_chat_assistant_calls_last_30d: int = Field(default=0, ge=0)
    llm_embedding_calls_last_30d: int = Field(default=0, ge=0)
    llm_on_prem_sensitive_calls_last_30d: int = Field(default=0, ge=0)
