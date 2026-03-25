"""Pydantic-Modelle für Cross-Regulation / Regelwerksgraph-API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegulatoryFrameworkOut(BaseModel):
    id: int
    key: str
    name: str
    description: str | None = None


class CrossRegFrameworkSummary(BaseModel):
    framework_key: str
    name: str
    subtitle: str = ""
    total_requirements: int
    covered_requirements: int
    gap_count: int
    coverage_percent: float = Field(ge=0.0, le=100.0)
    partial_count: int = 0
    planned_only_count: int = 0


class CrossRegulationSummaryResponse(BaseModel):
    tenant_id: str
    frameworks: list[CrossRegFrameworkSummary]


class RegulatoryRequirementOut(BaseModel):
    id: int
    framework_key: str
    framework_name: str
    code: str
    title: str
    description: str | None = None
    requirement_type: str
    criticality: str
    coverage_status: str
    linked_control_count: int
    primary_control_names: list[str] = Field(default_factory=list)
    related_framework_keys: list[str] = Field(default_factory=list)


class RegulatoryControlOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    control_type: str
    owner_role: str | None = None
    status: str
    requirement_count: int
    framework_count: int
    framework_keys: list[str] = Field(default_factory=list)


class RequirementControlLinkDetail(BaseModel):
    link_id: int
    control_id: str
    control_name: str
    coverage_level: str
    control_status: str
    owner_role: str | None = None
    ai_system_ids: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)


class RequirementControlsDetailResponse(BaseModel):
    requirement: RegulatoryRequirementOut
    links: list[RequirementControlLinkDetail]


class AISystemRegulatoryHintOut(BaseModel):
    requirement_id: int
    code: str
    title: str
    framework_key: str
    via_control_name: str


class CrossRegGapLinkedControlSnapshot(BaseModel):
    """Nur Metadaten (keine Freitext-Evidenz) für LLM-Gap-Kontext."""

    control_id: str
    name: str
    status: str
    coverage_level: str
    owner_role: str | None = None
    ai_system_ids: list[str] = Field(default_factory=list)
    policy_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)


class CrossRegGapRequirementItem(BaseModel):
    requirement_id: int
    framework_key: str
    code: str
    title: str
    criticality: str
    requirement_type: str
    coverage_status: str
    linked_controls: list[CrossRegGapLinkedControlSnapshot] = Field(default_factory=list)


class CrossRegulationGapsPayload(BaseModel):
    tenant_id: str
    tenant_industry_hint: str | None = None
    coverage: list[CrossRegFrameworkSummary]
    gaps: list[CrossRegGapRequirementItem]


class CrossRegLlmGapAssistantRequestBody(BaseModel):
    focus_frameworks: list[str] | None = None
    max_suggestions: int = Field(default=8, ge=1, le=10)


class CrossRegLlmGapSuggestion(BaseModel):
    requirement_ids: list[int]
    frameworks: list[str]
    recommendation_type: str
    suggested_control_name: str
    suggested_control_description: str
    rationale: str = ""
    priority: str
    suggested_owner_role: str
    suggested_actions: list[str] = Field(default_factory=list)


class CrossRegLlmGapAssistantResponse(BaseModel):
    tenant_id: str
    suggestions: list[CrossRegLlmGapSuggestion]
    gap_count_used: int = 0
