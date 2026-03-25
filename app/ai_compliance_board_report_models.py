"""Pydantic-Modelle: AI-Compliance-Board-Report (Assembler, API, Persistenz-Metadaten)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FrameworkCoverageSnapshot(BaseModel):
    framework_key: str
    name: str
    coverage_percent: float = Field(ge=0.0, le=100.0)
    total_requirements: int = Field(ge=0)
    covered_requirements: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    partial_count: int = Field(ge=0)
    planned_only_count: int = Field(ge=0)


class GapSnapshotBrief(BaseModel):
    requirement_id: int
    framework_key: str
    code: str
    title: str
    criticality: str
    requirement_type: str
    coverage_status: str
    linked_control_count: int = Field(ge=0)


class CompressedGapSuggestion(BaseModel):
    suggested_control_name: str
    priority: str
    frameworks: list[str] = Field(default_factory=list)
    requirement_codes: list[str] = Field(default_factory=list)
    recommendation_type: str = ""


class AIInventoryBrief(BaseModel):
    total_systems: int = Field(ge=0)
    high_risk_ai_systems: int = Field(
        ge=0,
        description="risk_level high oder unacceptable",
    )
    by_risk_level: list[dict[str, int | str]] = Field(default_factory=list)
    by_ai_act_category: list[dict[str, int | str]] = Field(default_factory=list)
    high_criticality_systems: int = Field(
        ge=0,
        description="criticality high oder very_high",
    )


class AiComplianceBoardReportInput(BaseModel):
    """Strukturierter Input für LLM (keine PII, keine Dokumentvolltexte)."""

    tenant_id: str
    audience_type: Literal["board", "management", "advisor_client"]
    language: str = "de"
    coverage: list[FrameworkCoverageSnapshot] = Field(default_factory=list)
    top_gaps: list[GapSnapshotBrief] = Field(default_factory=list)
    gap_assist_hints: list[CompressedGapSuggestion] = Field(default_factory=list)
    ai_inventory: AIInventoryBrief | None = None
    trend_note: str | None = Field(
        default=None,
        description="Hinweis, falls keine historische Zeitreihe vorliegt",
    )


class AiComplianceBoardReportCreateBody(BaseModel):
    audience_type: Literal["board", "management", "advisor_client"]
    focus_frameworks: list[str] | None = None
    include_ai_act_only: bool = False
    language: Literal["de"] = "de"
    period_start: datetime | None = None
    period_end: datetime | None = None


class AiComplianceBoardReportCreateResponse(BaseModel):
    report_id: str
    title: str
    rendered_markdown: str
    coverage_snapshot: list[FrameworkCoverageSnapshot]
    created_at: str
    audience_type: str


class AiComplianceBoardReportListItem(BaseModel):
    id: str
    title: str
    audience_type: str
    created_at: str


class AiComplianceBoardReportDetailResponse(BaseModel):
    id: str
    tenant_id: str
    title: str
    audience_type: str
    created_at: str
    rendered_markdown: str
    raw_payload: dict


class AdvisorBoardReportListRow(BaseModel):
    """Flache Zeile für Berater-Portfolio: Mandant + letzte/alle Reports."""

    tenant_id: str
    tenant_display_name: str | None = None
    report_id: str
    title: str
    audience_type: str
    created_at: str


class AdvisorBoardReportsPortfolioResponse(BaseModel):
    advisor_id: str
    reports: list[AdvisorBoardReportListRow]
