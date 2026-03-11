from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class IncidentSeverity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class IncidentStatus(StrEnum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class Incident(BaseModel):
    id: str
    created_at: datetime = Field(..., description="Erstellt am (UTC)")
    updated_at: datetime = Field(..., description="Letztes Update (UTC)")
    severity: IncidentSeverity
    status: IncidentStatus
    actor: str | None = Field(
        None,
        description="Auslösender Akteur (api_key / user / system)",
    )
    source: str | None = Field(
        None,
        description="Quell-Modul (policy_engine, manual, nis2_scan, ...)",
    )
    summary: str | None = Field(None, description="Regulatorische Kurzbeschreibung")
    metadata: dict[str, Any] | None = Field(
        None,
        description="Zusätzliche Key-Value-Daten",
    )
