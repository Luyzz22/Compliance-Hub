"""API-Modelle: AI & Compliance Readiness Score (0–100, Dimensionen, Level)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ReadinessLevel = Literal["basic", "managed", "embedded"]

__all__ = [
    "OperationalMonitoringExplanationStructured",
    "OamiExplainLevel",
    "ReadinessDimensionOut",
    "ReadinessExplanationStructured",
    "ReadinessLevel",
    "ReadinessScoreDimensions",
    "ReadinessScoreExplainResponse",
    "ReadinessScoreResponse",
    "ReadinessScoreSummary",
]


class ReadinessDimensionOut(BaseModel):
    """Eine Score-Dimension (0–1 intern, 0–100 für UI)."""

    normalized: float = Field(ge=0.0, le=1.0, description="Rohwert 0–1 vor Gewichtung")
    score_0_100: int = Field(ge=0, le=100, description="Gerundet normalized×100")


class ReadinessScoreDimensions(BaseModel):
    setup: ReadinessDimensionOut
    coverage: ReadinessDimensionOut
    kpi: ReadinessDimensionOut
    gaps: ReadinessDimensionOut
    reporting: ReadinessDimensionOut


class ReadinessScoreResponse(BaseModel):
    tenant_id: str
    score: int = Field(ge=0, le=100)
    level: ReadinessLevel
    interpretation: str = Field(
        default="",
        description="Kurzinterpretation (statisch aus Dimensionen, deutsch)",
    )
    dimensions: ReadinessScoreDimensions


class ReadinessScoreSummary(BaseModel):
    """Kompakt für Berater-Portfolio (ohne volle Dimensionen)."""

    score: int = Field(ge=0, le=100)
    level: ReadinessLevel


OamiExplainLevel = Literal["low", "medium", "high"]


class ReadinessExplanationStructured(BaseModel):
    """Structured LLM output; `level` uses API enum (UI maps to Basis/Etabliert/Integriert)."""

    score: int = Field(ge=0, le=100)
    level: ReadinessLevel
    short_reason: str = Field(default="", max_length=4000)
    drivers_positive: list[str] = Field(default_factory=list, max_length=8)
    drivers_negative: list[str] = Field(default_factory=list, max_length=8)
    regulatory_focus: str = Field(default="", max_length=2000)


class OperationalMonitoringExplanationStructured(BaseModel):
    """OAMI narrative from LLM; `level` uses API enum (UI maps to Niedrig/Mittel/Hoch)."""

    index: int | None = Field(default=None, ge=0, le=100)
    level: OamiExplainLevel | None = None
    recent_incidents_summary: str = Field(default="", max_length=2000)
    monitoring_gaps: list[str] = Field(default_factory=list, max_length=8)
    improvement_suggestions: list[str] = Field(default_factory=list, max_length=8)


class ReadinessScoreExplainResponse(BaseModel):
    """`explanation` für Legacy-Clients; optional strukturiert für Board-UI + Copy-Modul."""

    explanation: str
    provider: str = ""
    model_id: str = ""
    readiness_explanation: ReadinessExplanationStructured | None = None
    operational_monitoring_explanation: OperationalMonitoringExplanationStructured | None = None
