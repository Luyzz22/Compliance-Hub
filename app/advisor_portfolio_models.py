from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.advisor_client_snapshot_models import AdvisorTenantGovernanceBrief
from app.advisor_governance_maturity_brief_models import AdvisorGovernanceMaturityBrief
from app.readiness_score_models import ReadinessScoreSummary

GaiOamiLevel = Literal["low", "medium", "high"]


class GovernanceActivityPortfolioSummary(BaseModel):
    """Kurzform GAI für Berater-Portfolio (0–100 + Level)."""

    index: int = Field(ge=0, le=100)
    level: GaiOamiLevel


class OperationalMonitoringPortfolioSummary(BaseModel):
    """Kurzform OAMI für Berater-Portfolio."""

    index: int | None = Field(default=None, ge=0, le=100)
    level: GaiOamiLevel | None = None


class AdvisorPortfolioTenantEntry(BaseModel):
    """Eine Zeile im Berater-Portfolio (Meta-Ebene pro Mandant)."""

    tenant_id: str
    tenant_name: str
    industry: str | None = None
    country: str | None = None
    eu_ai_act_readiness: float = Field(ge=0.0, le=1.0)
    nis2_kritis_kpi_mean_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )
    nis2_kritis_systems_full_coverage_ratio: float = Field(ge=0.0, le=1.0)
    high_risk_systems_count: int = Field(ge=0)
    open_governance_actions_count: int = Field(ge=0)
    setup_completed_steps: int = Field(ge=0)
    setup_total_steps: int = Field(ge=1)
    setup_progress_ratio: float = Field(ge=0.0, le=1.0)
    governance_brief: AdvisorTenantGovernanceBrief | None = Field(
        default=None,
        description="Optional: Mandanten-Governance-Kurzinfo (ADVISOR_CLIENT_SNAPSHOT).",
    )
    readiness_summary: ReadinessScoreSummary | None = Field(
        default=None,
        description="Optional: Readiness Score (FEATURE_READINESS_SCORE).",
    )
    governance_activity_summary: GovernanceActivityPortfolioSummary | None = Field(
        default=None,
        description="Optional: GAI (FEATURE_GOVERNANCE_MATURITY).",
    )
    operational_monitoring_summary: OperationalMonitoringPortfolioSummary | None = Field(
        default=None,
        description="Optional: OAMI (FEATURE_GOVERNANCE_MATURITY).",
    )
    governance_maturity_advisor_brief: AdvisorGovernanceMaturityBrief | None = Field(
        default=None,
        description="Optional: Berater-Brief (FEATURE_GOVERNANCE_MATURITY).",
    )


class AdvisorPortfolioResponse(BaseModel):
    advisor_id: str
    generated_at_utc: datetime
    tenants: list[AdvisorPortfolioTenantEntry]
