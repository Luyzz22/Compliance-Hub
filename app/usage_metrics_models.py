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
