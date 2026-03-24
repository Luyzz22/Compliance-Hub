from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.ai_governance_action_models import AIGovernanceActionRead


class ReadinessRequirementTraffic(StrEnum):
    red = "red"
    amber = "amber"
    green = "green"


class ReadinessCriticalRequirement(BaseModel):
    """Top-Anforderung mit Ampel für EU-AI-Act-Readiness-Ansicht."""

    code: str = Field(description="Kürzel, z. B. EU AI Act Art. 9")
    name: str
    affected_systems_count: int = Field(ge=0)
    traffic: ReadinessRequirementTraffic
    priority: int = Field(ge=1, le=5, description="1 = höchste Priorität")


class SuggestedGovernanceAction(BaseModel):
    """Nicht persistiert; kann in eine echte Action übernommen werden."""

    related_requirement: str
    title: str
    rationale: str
    suggested_priority: int = Field(ge=1, le=5)


class EUAIActReadinessOverview(BaseModel):
    """Readiness bis Stichtag High-Risk (Standard 2026-08-02)."""

    tenant_id: str
    deadline: str
    days_remaining: int = Field(ge=0)
    overall_readiness: float = Field(ge=0.0, le=1.0)
    high_risk_systems_essential_complete: int = Field(ge=0)
    high_risk_systems_essential_incomplete: int = Field(ge=0)
    critical_requirements: list[ReadinessCriticalRequirement]
    suggested_actions: list[SuggestedGovernanceAction]
    open_governance_actions: list[AIGovernanceActionRead]
