"""Schemas für Remediation-Automation, Eskalationen und Reminder."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RemediationAutomationRunResponse(BaseModel):
    run_id: str
    escalations_created: int
    reminders_upserted: int
    events_written: int
    generated_actions: int
    rule_keys: list[str]


class RemediationEscalationListItem(BaseModel):
    id: str
    action_id: str
    severity: str
    reason_code: str
    detail: str | None
    status: str
    created_at_utc: datetime
    run_id: str | None = None


class RemediationEscalationListResponse(BaseModel):
    items: list[RemediationEscalationListItem]


class RemediationReminderListItem(BaseModel):
    id: str
    action_id: str
    kind: str
    remind_at_utc: datetime
    status: str
    created_at_utc: datetime
    run_id: str | None = None


class RemediationReminderListResponse(BaseModel):
    items: list[RemediationReminderListItem]


class RemediationAutomationSummary(BaseModel):
    """KPI-Überblick für Board/Workspace."""

    overdue_actions: int
    severe_escalations_open: int
    management_escalations_open: int
    reminders_due_today: int
    auto_generated_actions_7d: int


class AcknowledgeEscalationResponse(BaseModel):
    acknowledged: int
    escalation_ids: list[str] = Field(default_factory=list)
