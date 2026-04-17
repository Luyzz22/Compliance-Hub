"""Pydantic models for governance operations / operational resilience APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ServiceHealthSnapshotRead(BaseModel):
    id: str
    tenant_id: str
    poll_run_id: str
    source: str
    service_name: str
    status: str
    checked_at: datetime


class ServiceHealthIncidentRead(BaseModel):
    id: str
    tenant_id: str
    service_name: str
    previous_status: str | None
    current_status: str
    severity: str
    incident_state: str
    source: str
    detected_at: datetime
    resolved_at: datetime | None
    title: str
    summary: str


class OperationsKpisRead(BaseModel):
    last_checked_at: datetime | None
    open_incidents: int
    degraded_services: int
    down_services: int


class OperationalHealthPollRunResponse(BaseModel):
    tenants_processed: int
    snapshots_written: int
    incidents_opened: int
    incidents_resolved: int
    errors: list[str] = Field(default_factory=list)


class IncidentResolveRequest(BaseModel):
    """Optional actor hint for manual resolution (distinct from auto-resolve on health recovery)."""

    resolved_note: str | None = Field(default=None, max_length=2000)


class IncidentResolveResponse(BaseModel):
    id: str
    incident_state: str
    resolved_at: datetime
