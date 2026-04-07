from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ControlCenterSeverity(StrEnum):
    critical = "critical"
    warning = "warning"
    info = "info"


class ControlCenterSection(StrEnum):
    audit = "audit"
    incidents_reporting = "incidents_reporting"
    regulatory_deadlines = "regulatory_deadlines"
    register_export_obligations = "register_export_obligations"
    board_readiness = "board_readiness"
    integrations_connectors = "integrations_connectors"


class ControlCenterStatus(StrEnum):
    open = "open"
    due_soon = "due_soon"
    overdue = "overdue"
    blocked = "blocked"
    ok = "ok"


class EnterpriseControlCenterItem(BaseModel):
    section: ControlCenterSection
    severity: ControlCenterSeverity
    status: ControlCenterStatus
    title: str = Field(..., min_length=1, max_length=300)
    summary_de: str = Field(..., min_length=1, max_length=1000)
    due_at: datetime | None = None
    tenant_id: str
    source_type: str = Field(..., min_length=1, max_length=120)
    source_id: str = Field(..., min_length=1, max_length=255)
    action_label: str = Field(..., min_length=1, max_length=120)
    action_href: str = Field(..., min_length=1, max_length=500)


class EnterpriseControlCenterSectionGroup(BaseModel):
    section: ControlCenterSection
    label_de: str
    items: list[EnterpriseControlCenterItem]


class EnterpriseControlCenterSummaryCounts(BaseModel):
    critical: int = 0
    warning: int = 0
    info: int = 0
    total_open: int = 0


class EnterpriseControlCenterResponse(BaseModel):
    tenant_id: str
    generated_at_utc: datetime
    summary_counts: EnterpriseControlCenterSummaryCounts
    grouped_sections: list[EnterpriseControlCenterSectionGroup]
    top_urgent_items: list[EnterpriseControlCenterItem]
    markdown_de: str | None = None
