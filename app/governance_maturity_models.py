"""Governance Maturity Lens: Readiness + GAI + OAMI (API-Antworten)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

GaiLevel = Literal["low", "medium", "high"]
OamiStatus = Literal["active", "not_configured"]


class GovernanceActivityIndexComponents(BaseModel):
    s_D: float = Field(ge=0.0, le=1.0)
    s_F: float = Field(ge=0.0, le=1.0)
    s_K: float = Field(ge=0.0, le=1.0)
    s_E: float = Field(ge=0.0, le=1.0)
    D: int = Field(ge=0)
    F_eff: int = Field(ge=0)
    K: int = Field(ge=0, le=5)
    S: int = Field(ge=0)


class GovernanceReadinessBlock(BaseModel):
    score: int = Field(ge=0, le=100)
    level: str
    interpretation: str = ""


class GovernanceActivityBlock(BaseModel):
    index: int = Field(ge=0, le=100)
    level: GaiLevel
    window_days: int = 90
    last_computed_at: datetime
    components: GovernanceActivityIndexComponents | None = None


class OperationalAiMonitoringBlock(BaseModel):
    status: OamiStatus
    index: int | None = Field(default=None, ge=0, le=100)
    level: Literal["low", "medium", "high"] | None = None
    window_days: int | None = None
    message_de: str = ""
    drivers_de: list[str] = Field(default_factory=list, max_length=12)


class GovernanceMaturityResponse(BaseModel):
    tenant_id: str
    computed_at: datetime
    readiness: GovernanceReadinessBlock | None = None
    governance_activity: GovernanceActivityBlock
    operational_ai_monitoring: OperationalAiMonitoringBlock
    narrative_tag_ids: list[str] = Field(default_factory=list)
    readiness_display_score: int | None = Field(default=None, ge=0, le=100)
    readiness_score_adjustment_note: str | None = None
