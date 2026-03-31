"""Domain-Modelle für Berater-Funktionen (Mandanten-Steckbrief)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.advisor_governance_maturity_brief_models import AdvisorGovernanceMaturityBrief
from app.incident_drilldown_models import TenantIncidentDrilldownOut

RisikoNis2EntityCategory = Literal["none", "important_entity", "essential_entity"]


class TenantReportCriticalRequirementItem(BaseModel):
    """Kompakte Darstellung einer Top-Lücke (EU AI Act Readiness)."""

    code: str
    name: str
    affected_systems_count: int = Field(ge=0)


class AdvisorTenantReport(BaseModel):
    """Exportierbarer Mandanten-Steckbrief für Angebote, Reviews und Vorstand."""

    tenant_id: str
    tenant_name: str
    industry: str | None = None
    country: str | None = None
    generated_at_utc: datetime

    ai_systems_total: int = Field(ge=0)
    high_risk_systems_count: int = Field(ge=0)
    high_risk_with_full_controls_count: int = Field(ge=0)

    eu_ai_act_readiness_score: float = Field(ge=0.0, le=1.0)
    eu_ai_act_deadline: str
    eu_ai_act_days_remaining: int = Field(ge=0)

    nis2_incident_readiness_percent: float = Field(ge=0.0, le=100.0)
    nis2_supplier_risk_coverage_percent: float = Field(ge=0.0, le=100.0)
    nis2_ot_it_segregation_mean_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Mittelwert OT/IT-Segregation aus KPI-Tabelle, falls vorhanden.",
    )
    nis2_critical_focus_systems_count: int = Field(
        ge=0,
        description="Fokus-Systeme mit OT/IT-KPI unter Board-Schwelle (KRITIS-Heuristik).",
    )

    governance_open_actions_count: int = Field(ge=0)
    governance_overdue_actions_count: int = Field(ge=0)
    top_critical_requirements: list[TenantReportCriticalRequirementItem] = Field(
        default_factory=list,
        max_length=3,
    )

    setup_completed_steps: int = Field(ge=0)
    setup_total_steps: int = Field(ge=1)
    setup_open_step_labels: list[str] = Field(
        default_factory=list,
        description="Noch offene Guided-Setup-Schritte (Kurzlabels).",
    )
    executive_summary_narrative: str | None = Field(
        default=None,
        description=(
            "Optional sprachlich verdichtete Kurzfassung aus deterministischen Kennzahlen "
            "(LLM-Assist); keine neuen Fakten gegenüber den strukturierten Feldern."
        ),
    )
    governance_maturity_advisor_brief: AdvisorGovernanceMaturityBrief | None = Field(
        default=None,
        description=(
            "Optional: Berater-Kurzbrief (gleicher Kern wie Board governance_maturity_summary, "
            "plus Fokus und Zeithorizont)."
        ),
    )
    incident_drilldown_snapshot: TenantIncidentDrilldownOut | None = Field(
        default=None,
        description="90-Tage-Laufzeit-Incident-Drilldown (wie API) für Steckbrief-Markdown.",
    )

    risiko_nis2_scope_label_de: str = Field(
        default=(
            "Es liegt keine Einordnung als wichtige oder wesentliche Einrichtung nach NIS2 vor "
            "(bzw. außerhalb des relevanten NIS2-Scope in den Stammdaten geführt)."
        ),
        description="Fließtext zur NIS2-Stammdaten-Einordnung für den Risiko-Abschnitt.",
    )
    risiko_kritis_sector_label_de: str | None = Field(
        default=None,
        description="Anzeigename KRITIS-Sektor, falls hinterlegt.",
    )
    risiko_incidents_90d_count: int = Field(default=0, ge=0)
    risiko_incidents_90d_high_severity: int = Field(default=0, ge=0)
    risiko_incident_burden_level: Literal["low", "medium", "high"] = Field(
        default="low",
        description="Aggregierte Last 90 Tage (ohne Einzelfallinhalte).",
    )
    risiko_open_incidents_count: int = Field(default=0, ge=0)
    risiko_regulatory_priority_note_de: str | None = Field(
        default=None,
        description=(
            "Optional: gleicher erklärender Zusatz wie bei Portfolio-Priorität (Aufstock), "
            "falls die Heuristik greift."
        ),
    )
    risiko_nis2_entity_category: RisikoNis2EntityCategory | None = Field(
        default=None,
        description="Normalisierte NIS2-Kategorie für Templates.",
    )
