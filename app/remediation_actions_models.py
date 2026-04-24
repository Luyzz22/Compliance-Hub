"""Pydantic schemas for remediation & action tracking (governance layer)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RemediationLinkCreate(BaseModel):
    entity_type: str = Field(..., max_length=64, examples=["governance_control"])
    entity_id: str = Field(..., max_length=255)


class RemediationActionCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str | None = Field(default=None, max_length=8000)
    priority: str = Field(default="medium", pattern="^(critical|high|medium|low)$")
    owner: str | None = Field(default=None, max_length=320)
    due_at_utc: datetime | None = None
    category: str = Field(
        default="manual",
        pattern="^(manual|audit|control|incident|board|ai_act|nis2)$",
    )
    links: list[RemediationLinkCreate] = Field(default_factory=list)


class RemediationActionUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=8000)
    status: str | None = Field(
        default=None,
        pattern="^(open|in_progress|blocked|done|accepted_risk)$",
    )
    priority: str | None = Field(default=None, pattern="^(critical|high|medium|low)$")
    owner: str | None = Field(default=None, max_length=320)
    due_at_utc: datetime | None = None
    deferred_note: str | None = Field(default=None, max_length=8000)
    status_change_note: str | None = Field(
        default=None,
        max_length=2000,
        description="Optionaler Audit-Kommentar zur Statusänderung (erscheint in der Historie).",
    )


class RemediationCommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=8000)


class RemediationLinkRead(BaseModel):
    entity_type: str
    entity_id: str


class RemediationCommentRead(BaseModel):
    id: str
    body: str
    created_by: str | None
    created_at_utc: datetime


class RemediationStatusHistoryRead(BaseModel):
    id: str
    from_status: str | None
    to_status: str
    changed_at_utc: datetime
    changed_by: str | None
    note: str | None


class RemediationActionListItemRead(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    owner: str | None
    due_at_utc: datetime | None
    is_overdue: bool = False
    category: str
    rule_key: str | None
    updated_at_utc: datetime
    links: list[RemediationLinkRead] = Field(default_factory=list)


class RemediationSummaryRead(BaseModel):
    open_actions: int
    backlog_actions: int
    overdue_actions: int
    blocked_actions: int
    due_this_week: int


class RemediationActionListResponse(BaseModel):
    items: list[RemediationActionListItemRead]
    summary: RemediationSummaryRead


class RemediationActionDetailRead(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: str | None
    status: str
    priority: str
    owner: str | None
    due_at_utc: datetime | None
    is_overdue: bool = False
    category: str
    rule_key: str | None
    deferred_note: str | None
    created_at_utc: datetime
    updated_at_utc: datetime
    created_by: str | None
    links: list[RemediationLinkRead]
    comments: list[RemediationCommentRead]
    status_history: list[RemediationStatusHistoryRead]


class RemediationGenerateResponse(BaseModel):
    created_count: int
    rule_keys_touched: list[str]
    evaluated_at_utc: datetime
