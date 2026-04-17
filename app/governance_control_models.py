"""Pydantic schemas for Unified Control Layer (governance controls API)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ControlStatus = Literal[
    "not_started",
    "in_progress",
    "implemented",
    "needs_review",
    "overdue",
]

FrameworkTag = Literal["EU_AI_ACT", "ISO_42001", "ISO_27001", "ISO_27701", "NIS2"]


class FrameworkMappingCreate(BaseModel):
    framework: str = Field(..., max_length=64, examples=["NIS2"])
    clause_ref: str = Field(..., max_length=256, examples=["Art. 21 (1)"])
    mapping_note: str | None = Field(default=None, max_length=4000)


class FrameworkMappingRead(BaseModel):
    id: str
    framework: str
    clause_ref: str
    mapping_note: str | None = None


class GovernanceControlCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=8000)
    requirement_id: str | None = Field(default=None, max_length=36)
    status: ControlStatus = "not_started"
    owner: str | None = Field(default=None, max_length=320)
    next_review_at: datetime | None = None
    framework_tags: list[str] = Field(default_factory=list)
    framework_mappings: list[FrameworkMappingCreate] = Field(default_factory=list)
    source_inputs: dict = Field(
        default_factory=dict,
        description="Provenance / rule inputs (e.g. materialized_from_suggestion).",
    )


class GovernanceControlUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=8000)
    status: ControlStatus | None = None
    owner: str | None = Field(default=None, max_length=320)
    next_review_at: datetime | None = None
    framework_tags: list[str] | None = None


class GovernanceControlRead(BaseModel):
    id: str
    tenant_id: str
    requirement_id: str | None
    title: str
    description: str | None
    status: str
    owner: str | None
    next_review_at: datetime | None
    framework_tags: list[str]
    source_inputs: dict
    created_at_utc: datetime
    updated_at_utc: datetime
    created_by: str | None
    framework_mappings: list[FrameworkMappingRead] = Field(default_factory=list)


class GovernanceControlEvidenceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    body_text: str | None = Field(default=None, max_length=16000)
    source_type: str = Field(default="manual", max_length=64)
    source_ref: str | None = Field(default=None, max_length=256)


class GovernanceControlEvidenceRead(BaseModel):
    id: str
    control_id: str
    title: str
    body_text: str | None
    source_type: str
    source_ref: str | None
    created_at_utc: datetime
    created_by: str | None


class GovernanceControlStatusHistoryRead(BaseModel):
    id: str
    control_id: str
    from_status: str | None
    to_status: str
    changed_at_utc: datetime
    changed_by: str | None
    note: str | None


class GovernanceControlMaterializeRequest(BaseModel):
    """Idempotent: returns existing control if this suggestion_key was already materialized."""

    suggestion_key: str = Field(..., min_length=1, max_length=128)


class GovernanceControlsDashboardSummary(BaseModel):
    total_controls: int
    implemented: int
    in_progress: int
    not_started: int
    needs_review: int
    overdue_reviews: int


class GovernanceControlSuggestion(BaseModel):
    """Deterministic template; not persisted until user creates a control."""

    suggestion_key: str
    title: str
    description: str
    framework_tags: list[str]
    framework_mappings: list[FrameworkMappingCreate]
    triggered_by: dict = Field(default_factory=dict)
