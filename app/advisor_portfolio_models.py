from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.advisor_client_snapshot_models import AdvisorTenantGovernanceBrief
from app.advisor_governance_maturity_brief_models import AdvisorGovernanceMaturityBrief
from app.readiness_score_models import ReadinessScoreSummary

GaiOamiLevel = Literal["low", "medium", "high"]
AdvisorPortfolioPriority = Literal["high", "medium", "low"]
AdvisorMaturityScenarioHint = Literal["a", "b", "c", "d"]
Nis2EntityCategory = Literal["none", "important_entity", "essential_entity"]
IncidentBurdenLevel = Literal["low", "medium", "high"]


class GovernanceActivityPortfolioSummary(BaseModel):
    """Kurzform GAI für Berater-Portfolio (0–100 + Level)."""

    index: int = Field(ge=0, le=100)
    level: GaiOamiLevel


class OperationalMonitoringPortfolioSummary(BaseModel):
    """Kurzform OAMI für Berater-Portfolio."""

    index: int | None = Field(default=None, ge=0, le=100)
    level: GaiOamiLevel | None = None
    safety_related_runtime_incidents_90d: int = Field(
        default=0,
        ge=0,
        description="Laufzeit-Incidents (Subtype safety_violation) im OAMI-Fenster.",
    )
    availability_runtime_incidents_90d: int = Field(default=0, ge=0)
    oami_operational_hint_de: str | None = Field(
        default=None,
        max_length=400,
        description="Kurz: ob Sicherheits- vs. Verfügbarkeitslage den Index prägt.",
    )


class AdvisorPortfolioTenantEntry(BaseModel):
    """Eine Zeile im Berater-Portfolio (Meta-Ebene pro Mandant)."""

    tenant_id: str
    tenant_name: str
    industry: str | None = None
    country: str | None = None
    nis2_entity_category: Nis2EntityCategory = Field(
        default="none",
        description=(
            "Aus Mandantenfeld nis2_scope normalisiert: keine / wichtige / wesentliche Einrichtung."
        ),
    )
    kritis_sector_key: str | None = Field(
        default=None,
        description="Optionaler KRITIS-Sektorschlüssel aus Stammdaten (keine weiteren Details).",
    )
    recent_incidents_90d: bool = Field(
        default=False,
        description="Mind. ein strukturiertes Incident in den letzten 90 Tagen (Ja/Nein).",
    )
    incident_burden_level: IncidentBurdenLevel = Field(
        default="low",
        description="Incident-Last 90 Tage: low/medium/high (ohne Einzelfallinhalte).",
    )
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
    advisor_priority: AdvisorPortfolioPriority = Field(
        default="medium",
        description="Regelbasierte Beraterpriorität (hoch = zuerst klären).",
    )
    advisor_priority_sort_key: int = Field(
        default=1,
        ge=0,
        le=2,
        description="0=hoch, 1=mittel, 2=niedrig; aufsteigend sortieren für Dringlichkeit oben.",
    )
    advisor_priority_explanation_de: str = Field(
        default="",
        description="Kurzer Tooltip-Text zur Priorität (ohne LLM).",
    )
    maturity_scenario_hint: AdvisorMaturityScenarioHint | None = Field(
        default=None,
        description="Optional: Golden-Szenario A–D, wenn Kennzahlen zum Muster passen.",
    )
    primary_focus_tag_de: str = Field(
        default="Governance",
        description="Kompakter Hauptschwerpunkt (Monitoring, Readiness, Nutzung, Governance).",
    )


class AdvisorPortfolioResponse(BaseModel):
    advisor_id: str
    generated_at_utc: datetime
    tenants: list[AdvisorPortfolioTenantEntry]
