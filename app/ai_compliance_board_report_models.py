"""Pydantic-Modelle: AI-Compliance-Board-Report (Assembler, API, Persistenz-Metadaten)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.ai_governance_models import OamiIncidentSubtypeProfile
from app.governance_maturity_summary_models import GovernanceMaturitySummary


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


class BoardReportSystemKpiValueBrief(BaseModel):
    """Einzelmetrik für Board-LLM (High-Risk-System)."""

    kpi_key: str
    name: str
    unit: str
    latest_value: float
    trend: str


class BoardReportKpiSystemRowBrief(BaseModel):
    ai_system_id: str
    ai_system_name: str
    risk_level: str
    kpis: list[BoardReportSystemKpiValueBrief] = Field(default_factory=list)


class BoardReportKpiPortfolioRowBrief(BaseModel):
    kpi_key: str
    name: str
    unit: str
    avg_high_risk_latest: float | None = None
    trend_vs_prior_period: str = "flat"
    systems_with_data: int = Field(default=0, ge=0)


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
    high_risk_kpi_summaries: list[BoardReportKpiSystemRowBrief] = Field(
        default_factory=list,
        description="KPI-Snapshots je High-Risk-KI-System",
    )
    kpi_portfolio_aggregates: list[BoardReportKpiPortfolioRowBrief] = Field(
        default_factory=list,
        description="Aggregierte KPIs über High-Risk-Systeme",
    )
    governance_maturity_summary: GovernanceMaturitySummary | None = Field(
        default=None,
        description="Strukturierte Governance-Reife (Readiness/GAI/OAMI); UI mappt API-Enums.",
    )
    governance_maturity_executive_paragraph_de: str | None = Field(
        default=None,
        description="Fixer Executive-Overview-Absatz zur Governance-Reife (wörtlich übernehmen).",
    )
    oami_subtype_profile: OamiIncidentSubtypeProfile | None = Field(
        default=None,
        description=(
            "Optional: gewichtete OAMI-Incident-Subtypen (Board-Markdown-Parität, LLM-Kontext)."
        ),
    )
    temporal_langgraph_oami_system_id: str | None = Field(
        default=None,
        description="Temporal pilot: KI-System-ID für die LangGraph-OAMI-Erklärung.",
    )
    temporal_langgraph_oami_explanation: dict[str, object] | None = Field(
        default=None,
        description="Temporal pilot: OamiExplanationOut als Dict (LangGraph / Fallback).",
    )


class BoardReportWorkflowStartBody(BaseModel):
    snapshot_reference: str = "latest"
    audience_type: Literal["board", "management", "advisor_client"] = "board"
    primary_ai_system_id: str | None = None
    focus_frameworks: list[str] | None = None
    include_ai_act_only: bool = False
    language: Literal["de"] = "de"


class BoardReportWorkflowStartResponse(BaseModel):
    workflow_id: str
    run_id: str


class BoardReportWorkflowStatusResponse(BaseModel):
    workflow_id: str
    status: str
    report_id: str | None = None


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
