"""Structured governance maturity executive summary for Board reports (API enums, DE narrative)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ReadinessLevelApi = Literal["basic", "managed", "embedded"]
IndexLevelApi = Literal["low", "medium", "high"]


class GovernanceMaturityReadinessSlice(BaseModel):
    score: int = Field(ge=0, le=100)
    level: ReadinessLevelApi
    short_reason: str = Field(default="", max_length=4000)


class GovernanceMaturityActivitySlice(BaseModel):
    index: int = Field(ge=0, le=100)
    level: IndexLevelApi
    short_reason: str = Field(default="", max_length=4000)


class GovernanceMaturityOperationalMonitoringSlice(BaseModel):
    index: int | None = Field(default=None, ge=0, le=100)
    level: IndexLevelApi | None = None
    short_reason: str = Field(default="", max_length=4000)


class GovernanceMaturityOverallAssessment(BaseModel):
    """Aggregate Board signal; `level` uses same index scale as GAI/OAMI (low | medium | high)."""

    level: IndexLevelApi
    short_summary: str = Field(default="", max_length=4000)
    key_risks: list[str] = Field(default_factory=list, max_length=5)
    key_strengths: list[str] = Field(default_factory=list, max_length=5)


class GovernanceMaturitySummary(BaseModel):
    readiness: GovernanceMaturityReadinessSlice
    activity: GovernanceMaturityActivitySlice
    operational_monitoring: GovernanceMaturityOperationalMonitoringSlice
    overall_assessment: GovernanceMaturityOverallAssessment


class GovernanceMaturityBoardSummaryParseResult(BaseModel):
    """Result of LLM parse + snapshot alignment."""

    summary: GovernanceMaturitySummary
    executive_overview_governance_maturity_de: str = Field(default="", max_length=8000)
    parse_ok: bool = True
    used_llm_paragraph: bool = True
