from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.enterprise_integration_blueprint_models import EvidenceDomain, SourceSystemType


class ConnectorConnectionStatus(StrEnum):
    not_configured = "not_configured"
    connected = "connected"
    degraded = "degraded"


class ConnectorSyncStatus(StrEnum):
    idle = "idle"
    running = "running"
    success = "success"
    failed = "failed"


class ConnectorInstanceRuntime(BaseModel):
    connector_instance_id: str
    tenant_id: str
    source_system_type: SourceSystemType
    connection_status: ConnectorConnectionStatus
    sync_status: ConnectorSyncStatus
    last_sync_at: datetime | None = None
    last_error: str | None = None
    enabled_evidence_domains: list[EvidenceDomain] = Field(default_factory=list)


class ConnectorSyncResult(BaseModel):
    sync_run_id: str
    tenant_id: str
    connector_instance_id: str
    sync_status: ConnectorSyncStatus
    started_at_utc: datetime
    finished_at_utc: datetime | None = None
    records_ingested: int = 0
    last_error: str | None = None
    summary_de: str


class ConnectorRuntimeStatusResponse(BaseModel):
    tenant_id: str
    connector_instance: ConnectorInstanceRuntime
    last_sync_result: ConnectorSyncResult | None = None


class ConnectorManualSyncResponse(BaseModel):
    tenant_id: str
    connector_instance: ConnectorInstanceRuntime
    sync_result: ConnectorSyncResult
    normalized_records_preview: list[dict[str, str]] = Field(default_factory=list)
