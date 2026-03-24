from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Nis2KritisKpiType(StrEnum):
    INCIDENT_RESPONSE_MATURITY = "INCIDENT_RESPONSE_MATURITY"
    SUPPLIER_RISK_COVERAGE = "SUPPLIER_RISK_COVERAGE"
    OT_IT_SEGREGATION = "OT_IT_SEGREGATION"


class Nis2KritisKpi(BaseModel):
    id: str
    ai_system_id: str
    kpi_type: Nis2KritisKpiType
    value_percent: int = Field(ge=0, le=100)
    evidence_ref: str | None = None
    last_reviewed_at: datetime | None = None


class Nis2KritisKpiUpsertRequest(BaseModel):
    kpi_type: Nis2KritisKpiType
    value_percent: int = Field(ge=0, le=100)
    evidence_ref: str | None = None
    last_reviewed_at: datetime | None = None


class Nis2KritisKpiRecommended(BaseModel):
    """Empfohlene Zielwerte aus dem gemappten High-Risk-Szenario-Profil."""

    scenario_profile_id: str | None = None
    scenario_label: str | None = None
    incident_response_maturity_percent: int | None = Field(default=None, ge=0, le=100)
    supplier_risk_coverage_percent: int | None = Field(default=None, ge=0, le=100)
    ot_it_segregation_percent: int | None = Field(default=None, ge=0, le=100)


class Nis2KritisKpiListResponse(BaseModel):
    kpis: list[Nis2KritisKpi]
    recommended: Nis2KritisKpiRecommended | None = None


class Nis2KritisTenantKpiAggregate(BaseModel):
    """Aggregat für Governance-/Board-KPIs."""

    mean_percent: float | None = Field(
        default=None,
        description="Mittelwert aller gespeicherten KPI-Werte (0–100).",
    )
    systems_with_all_three_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Anteil KI-Systeme mit je einem Eintrag pro KPI-Typ (0–1).",
    )
