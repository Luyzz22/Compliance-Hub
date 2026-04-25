"""Pydantic models — Governance Workflow Orchestration (MVP, deterministische Regeln)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

WorkflowTaskStatus = Literal["open", "in_progress", "done", "cancelled", "escalated"]


class GovernanceWorkflowKpisRead(BaseModel):
    open_tasks: int
    overdue_tasks: int
    escalated_tasks: int
    notifications_queued: int
    workflow_events_24h: int


class GovernanceWorkflowTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    title: str
    description: str
    default_sla_days: int
    is_system: int


class GovernanceWorkflowRunRead(BaseModel):
    id: str
    tenant_id: str
    trigger_mode: str
    status: str
    rule_bundle_version: str
    summary: dict[str, Any]
    started_at_utc: datetime
    completed_at_utc: datetime | None


class GovernanceWorkflowDashboardRead(BaseModel):
    kpis: GovernanceWorkflowKpisRead
    rule_bundle_version: str
    recent_runs: list[GovernanceWorkflowRunRead]
    templates: list[GovernanceWorkflowTemplateRead]


class GovernanceWorkflowRunRequest(BaseModel):
    """Optional Profil-Label für künftige getrennte Regel-Sets (MVP: nur 'default')."""

    rule_profile: str = "default"


class GovernanceWorkflowRunResponse(BaseModel):
    run_id: str
    status: str
    tasks_materialized: int
    events_written: int
    notifications_queued: int
    rule_bundle_version: str


class GovernanceWorkflowTaskListItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: str
    priority: str
    source_type: str
    source_id: str
    assignee_user_id: str | None
    due_at_utc: datetime | None
    template_code: str | None
    framework_tags: list[str]
    escalation_level: int
    created_at_utc: datetime
    updated_at_utc: datetime
    is_overdue: bool


class GovernanceWorkflowTaskHistoryRead(BaseModel):
    at_utc: datetime
    from_status: str | None
    to_status: str
    actor_id: str
    note: str | None
    payload_json: dict[str, Any] = Field(default_factory=dict)


class GovernanceWorkflowTaskDetailRead(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: str | None
    status: str
    priority: str
    source_type: str
    source_id: str
    source_ref: dict[str, Any]
    assignee_user_id: str | None
    due_at_utc: datetime | None
    template_code: str | None
    framework_tags: list[str]
    last_comment: str | None
    run_id: str | None
    created_at_utc: datetime
    updated_at_utc: datetime
    is_overdue: bool
    history: list[GovernanceWorkflowTaskHistoryRead]


class GovernanceWorkflowTaskUpdate(BaseModel):
    status: str | None = Field(
        default=None,
        description="open, in_progress, done, cancelled, escalated; ungültige Werte → 422",
    )
    assignee_user_id: str | None = Field(
        default=None,
        description="Feld explizit mit `null` senden, um Bearbeiter zu leeren (PATCH-JSON).",
    )
    last_comment: str | None = Field(
        default=None, max_length=5000, description="Kommentar / Zusatz zur letzten Änderung"
    )


class GovernanceWorkflowEventRead(BaseModel):
    id: str
    at_utc: datetime
    event_type: str
    severity: str
    ref_task_id: str | None
    source_type: str
    source_id: str
    message: str
    payload_json: dict[str, Any]


class GovernanceNotificationTestRequest(BaseModel):
    channel: str = "test"
    title: str = "MVP Test-Benachrichtigung"
    body: str = "Dieser Eintrag dient dem Audit-Trail; kein echter E-Mail-Versand im MVP."
    ref_task_id: str | None = None


class GovernanceNotificationTestResponse(BaseModel):
    notification_id: str
    delivery_id: str
    result: str


class GovernanceNotificationRead(BaseModel):
    id: str
    ref_task_id: str | None
    channel: str
    status: str
    title: str
    body_text: str
    created_at_utc: datetime


class GovernanceNotificationDeliveryRead(BaseModel):
    id: str
    notification_id: str
    channel: str
    result: str
    detail: str | None
    delivered_at_utc: datetime
