from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DeadlineCategory(StrEnum):
    EU_AI_ACT = "eu_ai_act"
    NIS2 = "nis2"
    ISO_27001 = "iso_27001"
    ISO_42001 = "iso_42001"
    DSGVO = "dsgvo"
    GOBD = "gobd"
    KRITIS = "kritis"
    CUSTOM = "custom"


class DeadlineStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class EscalationLevel(StrEnum):
    NONE = "none"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    OVERDUE = "overdue"


class ComplianceDeadlineCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    category: DeadlineCategory
    due_date: date
    owner: str | None = None
    regulation_reference: str | None = None
    recurrence_months: int | None = None
    status: DeadlineStatus = DeadlineStatus.OPEN


class ComplianceDeadlineResponse(BaseModel):
    id: str
    tenant_id: str | None = None
    title: str
    description: str | None = None
    category: DeadlineCategory
    due_date: date
    status: DeadlineStatus = DeadlineStatus.OPEN
    owner: str | None = None
    regulation_reference: str | None = None
    recurrence_months: int | None = None
    is_system: bool = False
    source_type: str | None = None
    source_id: str | None = None
    escalation_level: EscalationLevel
    days_remaining: int
    created_at_utc: datetime


class ComplianceDeadlineUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    owner: str | None = None
    status: DeadlineStatus | None = None
