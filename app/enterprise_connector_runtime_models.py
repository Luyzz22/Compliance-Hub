from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.enterprise_integration_blueprint_models import EvidenceDomain, SourceSystemType


class ConnectorConnectionStatus(StrEnum):
    not_configured = "not_configured"
    connected = "connected"
    degraded = "degraded"


class ConnectorInstanceSyncState(StrEnum):
    """High-level connector instance state (last known operational posture)."""

    idle = "idle"
    running = "running"
    succeeded = "succeeded"
    partial_success = "partial_success"
    failed = "failed"


class SyncRunLifecycle(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    partial_success = "partial_success"
    failed = "failed"
    cancelled = "cancelled"


class ConnectorFailureCategory(StrEnum):
    auth_config = "auth_config"
    source_unavailable = "source_unavailable"
    payload_validation = "payload_validation"
    normalization_mapping = "normalization_mapping"
    internal_processing = "internal_processing"


class ConnectorInstanceRuntime(BaseModel):
    connector_instance_id: str
    tenant_id: str
    source_system_type: SourceSystemType
    connection_status: ConnectorConnectionStatus
    sync_status: ConnectorInstanceSyncState
    last_sync_at: datetime | None = None
    last_error: str | None = None
    enabled_evidence_domains: list[EvidenceDomain] = Field(default_factory=list)


class ConnectorSyncResult(BaseModel):
    sync_run_id: str
    tenant_id: str
    connector_instance_id: str
    sync_status: SyncRunLifecycle
    started_at_utc: datetime
    finished_at_utc: datetime | None = None
    duration_ms: int | None = None
    records_received: int = 0
    records_normalized: int = 0
    records_rejected: int = 0
    records_ingested: int = 0
    failure_category: ConnectorFailureCategory | None = None
    retry_of_sync_run_id: str | None = None
    retry_recommended: bool = False
    operator_next_step_de: str = ""
    last_error: str | None = None
    summary_de: str


class ConnectorHealthSnapshot(BaseModel):
    connection_status: ConnectorConnectionStatus
    last_terminal_sync: SyncRunLifecycle | None = None
    last_finished_at_utc: datetime | None = None
    last_failure_category: ConnectorFailureCategory | None = None
    evidence_record_count: int = 0
    has_material_connector_issue: bool = False
    material_issue_summary_de: str | None = None


class ConnectorRuntimeStatusResponse(BaseModel):
    tenant_id: str
    connector_instance: ConnectorInstanceRuntime
    last_sync_result: ConnectorSyncResult | None = None
    health: ConnectorHealthSnapshot


class ConnectorSyncHistoryResponse(BaseModel):
    tenant_id: str
    runs: list[ConnectorSyncResult]


class ConnectorManualSyncResponse(BaseModel):
    tenant_id: str
    connector_instance: ConnectorInstanceRuntime
    sync_result: ConnectorSyncResult
    normalized_records_preview: list[dict[str, str]] = Field(default_factory=list)


class ConnectorRetrySyncBody(BaseModel):
    """Optional explicit run to retry; omit to retry the latest failed/partial run."""

    sync_run_id: str | None = Field(default=None, max_length=120)
