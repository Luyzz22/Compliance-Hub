"""API-Modelle: AI Runtime Events Ingest & Operational Monitoring Index (OAMI)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RuntimeEventType = Literal[
    "incident",
    "metric_threshold_breach",
    "deployment_change",
    "heartbeat",
    "metric_snapshot",
]

RuntimeEventSource = Literal[
    "sap_ai_core",
    "sap_btp_event_mesh",
    "manual_import",
    "other_provider",
]

OamiLevel = Literal["low", "medium", "high"]


class RuntimeEventIn(BaseModel):
    """Kanonisches Ingest-Event (keine PII, kein Freitext außer technischen IDs)."""

    source_event_id: str = Field(min_length=1, max_length=128)
    source: RuntimeEventSource | str = Field(max_length=64)
    event_type: RuntimeEventType | str = Field(max_length=64)
    severity: str | None = Field(default=None, max_length=32)
    occurred_at: datetime
    metric_key: str | None = Field(default=None, max_length=128)
    incident_code: str | None = Field(default=None, max_length=128)
    value: float | None = None
    delta: float | None = None
    threshold_breached: bool | None = None
    environment: str | None = Field(default=None, max_length=64)
    model_version: str | None = Field(default=None, max_length=255)
    extra: dict[str, object] = Field(default_factory=dict)


class RuntimeEventsBatchIn(BaseModel):
    events: list[RuntimeEventIn] = Field(min_length=1, max_length=500)


class RuntimeEventsIngestResult(BaseModel):
    inserted: int
    skipped_duplicate: int
    kpi_updates: int = 0


class OamiComponentsOut(BaseModel):
    freshness: float = Field(ge=0.0, le=1.0, description="Letzte Aktivität vs. Stille")
    activity_days: float = Field(ge=0.0, le=1.0, description="Distinct Tage mit Events")
    incident_stability: float = Field(ge=0.0, le=1.0, description="Weniger high/critical besser")
    metric_stability: float = Field(ge=0.0, le=1.0, description="Weniger Schwellenverletzungen besser")


class SystemMonitoringIndexOut(BaseModel):
    ai_system_id: str
    tenant_id: str
    window_days: int
    operational_monitoring_index: int = Field(ge=0, le=100)
    level: OamiLevel
    has_data: bool
    last_event_at: datetime | None
    incident_count: int = 0
    high_severity_incident_count: int = 0
    metric_threshold_breach_count: int = 0
    distinct_active_days: int = 0
    components: OamiComponentsOut


class TenantOperationalMonitoringIndexOut(BaseModel):
    tenant_id: str
    window_days: int
    operational_monitoring_index: int = Field(ge=0, le=100)
    level: OamiLevel
    systems_scored: int
    has_any_runtime_data: bool
    components: OamiComponentsOut | None = None
