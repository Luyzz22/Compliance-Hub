from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IncidentSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"


class IncidentTimelineItem(BaseModel):
    """Einzelner Eintrag in der Incident-Timeline."""

    id: str = Field(..., description="UUID des Incidents")
    ai_system_id: str | None = Field(None, description="Referenz auf betroffenes AI-System")
    title: str = Field(..., description="Kurztitel des Incidents (EU AI Act Art. 73 konform)")
    severity: IncidentSeverity = Field(..., description="Schweregrad")
    status: IncidentStatus = Field(..., description="Aktueller Status")
    created_at: datetime = Field(..., description="Erstellzeitpunkt (UTC)")
    updated_at: datetime = Field(..., description="Letztes Update (UTC)")
    actor: str | None = Field(None, description="Auslösender Akteur (api_key / user / system)")
    source: str | None = Field(None, description="Quell-Modul (policy_engine, manual, nis2_scan, ...)")
    summary: str | None = Field(None, description="Regulatorische Kurzbeschreibung")
    metadata: dict[str, Any] | None = Field(None, description="Zusätzliche Key-Value-Daten")

    model_config = {"from_attributes": True}


class IncidentKPIs(BaseModel):
    """Aggregierte KPIs für den KPI-Header im Dashboard."""

    total: int
    open: int
    in_progress: int
    resolved: int
    critical_open: int
    high_open: int
