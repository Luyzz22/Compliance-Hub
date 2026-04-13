"""Typed event definitions for the enterprise audit trail (Phase 10)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class AuditActionCategory(StrEnum):
    AUTH = "auth"
    ROLE_CHANGE = "role_change"
    FEATURE_ACCESS = "feature_access"
    BILLING = "billing"
    DATA_ACCESS = "data_access"
    ADMIN = "admin"
    TRUST_CENTER = "trust_center"


class AlertSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditLogFilter(BaseModel):
    actor: str | None = None
    action: str | None = None
    resource_type: str | None = None
    severity: str | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None


class AuditLogItem(BaseModel):
    id: int
    tenant_id: str
    actor: str
    action: str
    entity_type: str
    entity_id: str
    before: str | None = None
    after: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    previous_hash: str | None = None
    entry_hash: str | None = None
    created_at_utc: datetime
    actor_role: str | None = None
    outcome: str | None = None
    correlation_id: str | None = None
    metadata_json: str | None = None


class AuditLogPage(BaseModel):
    items: list[AuditLogItem] = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    has_next: bool = False


class AuditAlertItem(BaseModel):
    id: str
    tenant_id: str
    audit_log_id: int | None = None
    severity: str
    alert_type: str
    title: str
    description: str | None = None
    actor: str | None = None
    ip_address: str | None = None
    resolved: bool = False
    resolved_by: str | None = None
    resolved_at: datetime | None = None
    created_at_utc: datetime


class ChainIntegrityResult(BaseModel):
    valid: bool
    checked_count: int
    first_invalid_id: int | None = None


class VVTEntry(BaseModel):
    processing_activity: str
    data_categories: list[str]
    purpose: str
    legal_basis: str
    recipients: list[str]
    retention_period: str
    technical_measures: list[str]


class VVTExport(BaseModel):
    tenant_id: str
    generated_at: datetime
    entries: list[VVTEntry]
    total_processing_activities: int
