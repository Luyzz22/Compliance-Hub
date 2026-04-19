"""Pydantic schemas for audit readiness and evidence completeness (governance audits API)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GovernanceAuditCaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=8000)
    framework_tags: list[str] = Field(
        ...,
        min_length=1,
        description="In-scope frameworks, e.g. EU_AI_ACT, ISO_42001, ISO_27001, ISO_27701, NIS2",
    )
    control_ids: list[str] | None = Field(
        default=None,
        description=(
            "If omitted, tenant controls whose tags intersect framework_tags are attached."
        ),
    )


class GovernanceAuditCaseRead(BaseModel):
    id: str
    tenant_id: str
    title: str
    description: str | None
    status: str
    framework_tags: list[str]
    control_ids: list[str]
    created_at_utc: datetime
    updated_at_utc: datetime
    created_by: str | None


class AuditReadinessFrameworkSlice(BaseModel):
    framework_tag: str
    controls_in_scope: int
    controls_ready: int
    evidence_gap_count: int
    readiness_pct: float = Field(..., description="0–100, deterministic MVP aggregate.")


class AuditEvidenceGapRow(BaseModel):
    control_id: str
    control_title: str
    missing_evidence_type_key: str
    label_hint: str
    priority: int = Field(..., ge=1, le=3, description="1=critical … 3=normal (MVP heuristic).")
    recommended_action_de: str


class AuditReadinessSummaryRead(BaseModel):
    audit_case_id: str
    overall_readiness_pct: float
    controls_total: int
    controls_ready: int
    evidence_gap_count: int
    overdue_reviews_count: int
    by_framework: list[AuditReadinessFrameworkSlice]
    gaps: list[AuditEvidenceGapRow] = Field(default_factory=list)


class AuditReadinessControlRow(BaseModel):
    control_id: str
    title: str
    framework_tags: list[str]
    status: str
    owner: str | None
    evidence_completeness_pct: float
    missing_evidence_types: list[str]
    next_review_at: datetime | None
    is_ready: bool
    review_overdue: bool


class GovernanceAuditTrailRow(BaseModel):
    created_at_utc: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: str
    outcome: str | None
