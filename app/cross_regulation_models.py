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
