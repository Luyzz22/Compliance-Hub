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
    requirement_id: str | None = Field(
        default=None,
        description="Interne Requirement-ID (Compliance-Gap), z. B. art9_risk_management.",
    )
    related_ai_system_ids: list[str] = Field(
        default_factory=list,
        description="KI-Systeme mit Lücke zu dieser Anforderung (Deep-Link zur Registry).",
        max_length=100,
    )
    linked_governance_action_ids: list[str] = Field(
        default_factory=list,
        description="Offene/in Bearbeitung befindliche Maßnahmen mit Bezug zu dieser Anforderung.",
        max_length=50,
    )
    open_actions_count_for_requirement: int = Field(
        default=0,
        ge=0,
        description="Anzahl verknüpfter offener Maßnahmen (Badge).",
    )


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
