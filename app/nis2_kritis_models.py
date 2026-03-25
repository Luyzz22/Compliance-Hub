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


class Nis2KritisKpiHistogramBucket(BaseModel):
    """Histogramm-Bucket für Verteilung der KPI-Prozentwerte."""

    range_min_inclusive: int = Field(ge=0, le=100)
    range_max_exclusive: int = Field(ge=0, le=101)
    count: int = Field(ge=0)


class Nis2KritisKpiCriticalSystemEntry(BaseModel):
    """KI-System mit niedrigem KPI-Wert (Worst-Offenders)."""

    ai_system_id: str
    name: str
    business_unit: str
    kpi_type: Nis2KritisKpiType
    value_percent: int = Field(ge=0, le=100)
    detail_href: str = Field(
        description="Frontend-Pfad zur Pflege (EU-AI-Act-/Gap-Ansicht).",
    )


class Nis2KritisKpiTypeDrilldown(BaseModel):
    """Histogramm + Top-N je KPI-Typ."""

    kpi_type: Nis2KritisKpiType
    histogram: list[Nis2KritisKpiHistogramBucket]
    critical_systems: list[Nis2KritisKpiCriticalSystemEntry]


class Nis2KritisKpiDrilldown(BaseModel):
    """Tenant-weite Drilldown-Sicht für NIS2-/KRITIS-KPIs."""

    tenant_id: str
    generated_at: datetime
    top_n: int = Field(ge=1, le=50)
    by_kpi_type: list[Nis2KritisKpiTypeDrilldown]


class Nis2KritisKpiSuggestionRequest(BaseModel):
    """Freitext-Kontext für KI-Vorschläge (keine automatische Persistenz)."""

    ai_system_id: str = Field(..., min_length=1)
    free_text: str = Field(
        ...,
        min_length=10,
        max_length=32000,
        description="Aggregierte Beschreibung: Controls, Runbooks, Prozesse, Doku.",
    )


class Nis2KritisKpiSuggestionBody(BaseModel):
    """Nur Request-Body; ai_system_id kommt aus der URL."""

    free_text: str = Field(
        ...,
        min_length=10,
        max_length=32000,
    )


class Nis2KritisKpiSuggestion(BaseModel):
    kpi_type: Nis2KritisKpiType
    suggested_value_percent: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(..., max_length=4000)


class Nis2KritisKpiSuggestionResponse(BaseModel):
    ai_system_id: str
    suggestions: list[Nis2KritisKpiSuggestion]
