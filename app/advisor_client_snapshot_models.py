"""API-Modelle: Mandanten-Governance-Snapshot für Berater."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.readiness_score_models import ReadinessScoreResponse


class ClientInfoSnapshot(BaseModel):
    tenant_id: str
    display_name: str
    industry: str | None = None
    country: str | None = None
    tenant_kind: str | None = Field(
        default=None,
        description="Aus AI-Governance-Setup-Wizard: enterprise | advisor",
    )
    registry_nis2_scope: str | None = None
    registry_ai_act_scope: str | None = None


class SetupStatusSnapshot(BaseModel):
    guided_setup_completed_steps: int = Field(ge=0)
    guided_setup_total_steps: int = Field(ge=1)
    ai_governance_wizard_progress_steps: list[int] = Field(default_factory=list)
    ai_governance_wizard_steps_total: int = 6
    ai_governance_wizard_marked_steps: list[int] = Field(default_factory=list)


class FrameworkScopeSnapshot(BaseModel):
    active_frameworks: list[str] = Field(default_factory=list)
    compliance_scopes: list[str] = Field(default_factory=list)


class AiSystemsSummarySnapshot(BaseModel):
    total_count: int = Field(ge=0)
    high_risk_count: int = Field(ge=0)
    nis2_critical_count: int = Field(
        ge=0,
        description="KI-Systeme mit criticality very_high",
    )
    by_risk_level: dict[str, int] = Field(default_factory=dict)


class KpiSummarySnapshot(BaseModel):
    high_risk_systems_in_scope: int = Field(ge=0)
    systems_with_kpi_values: int = Field(ge=0)
    critical_kpi_system_rows: int = Field(ge=0)
    aggregate_trends_non_flat: int = Field(
        ge=0,
        description="Anzahl KPI-Definitionen mit erkennbarem Trend (nicht flat)",
    )


class CrossRegFrameworkSnapshot(BaseModel):
    framework_key: str
    name: str
    coverage_percent: float
    gap_count: int = Field(ge=0)
    total_requirements: int = Field(ge=0)


class ReportsSummarySnapshot(BaseModel):
    reports_total: int = Field(ge=0)
    last_report_id: str | None = None
    last_report_created_at: datetime | None = None
    last_report_audience: str | None = None
    last_report_title: str | None = None


class GapAssistSnapshot(BaseModel):
    regulatory_gap_items_count: int = Field(ge=0)
    llm_gap_suggestions_count: int | None = Field(
        default=None,
        description="Optional: nur wenn LLM-Gap-Assist ausgeführt wurde / verfügbar",
    )


class AdvisorTenantGovernanceBrief(BaseModel):
    """Kompakte Zeile fürs Berater-Portfolio (optional)."""

    wizard_progress_count: int = Field(ge=0, le=6)
    wizard_steps_total: int = 6
    active_framework_keys: list[str] = Field(default_factory=list)
    cross_reg_mean_coverage_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )
    regulatory_gap_count: int = Field(ge=0)
    nis2_critical_ai_count: int = Field(ge=0)


class AdvisorClientGovernanceSnapshotResponse(BaseModel):
    advisor_id: str
    client_tenant_id: str
    generated_at_utc: datetime
    client_info: ClientInfoSnapshot
    setup_status: SetupStatusSnapshot
    framework_scope: FrameworkScopeSnapshot
    ai_systems_summary: AiSystemsSummarySnapshot
    kpi_summary: KpiSummarySnapshot
    cross_reg_summary: list[CrossRegFrameworkSnapshot] = Field(default_factory=list)
    gap_assist: GapAssistSnapshot
    reports_summary: ReportsSummarySnapshot
    readiness: ReadinessScoreResponse | None = Field(
        default=None,
        description="Optional: AI & Compliance Readiness (FEATURE_READINESS_SCORE).",
    )


class AdvisorGovernanceSnapshotMarkdownResponse(BaseModel):
    markdown: str
    provider: str = ""
    model_id: str = ""
