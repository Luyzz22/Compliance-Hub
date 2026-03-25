"""API-Modelle: AI & Compliance Readiness Score (0–100, Dimensionen, Level)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ReadinessLevel = Literal["basic", "managed", "embedded"]

__all__ = [
    "ReadinessDimensionOut",
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


class ReadinessScoreExplainResponse(BaseModel):
    explanation: str
    provider: str = ""
    model_id: str = ""
