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
    summary: str | None = Field(
        None,
        description="Regulatorische Kurzbeschreibung",
    )
    metadata: dict[str, Any] | None = Field(
        None,
        description="Zusätzliche Key-Value-Daten",
    )


# ─── Board / AI Governance Incident Overview (NIS2 Art. 21/23, ISO 42001) ─────


class BySeverityEntry(BaseModel):
    """Anzahl Incidents pro Schweregrad für Board-Drilldown."""

    severity: IncidentSeverity
    count: int


class AIIncidentOverview(BaseModel):
    """Übersicht Incidents für Board-KPI-Drilldown (NIS2, ISO 42001 Incident Management)."""

    tenant_id: str
    total_incidents_last_12_months: int
    open_incidents: int
    major_incidents_last_12_months: int
    mean_time_to_ack_hours: float | None = None
    mean_time_to_recover_hours: float | None = None
    by_severity: list[BySeverityEntry]


class AIIncidentBySystemEntry(BaseModel):
    """Pro KI-System: Incident-Anzahl und letztes Incident für Board-Drilldown."""

    ai_system_id: str
    ai_system_name: str
    incident_count: int
    last_incident_at: datetime | None = None
