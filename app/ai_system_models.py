from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AISystemRiskLevel(StrEnum):
    low = "low"
    limited = "limited"
    high = "high"
    unacceptable = "unacceptable"


class AIActCategory(StrEnum):
    prohibited = "prohibited"
    high_risk = "high_risk"
    limited_risk = "limited_risk"
    minimal_risk = "minimal_risk"


class AISystemStatus(StrEnum):
    draft = "draft"
    in_review = "in_review"
    active = "active"
    retired = "retired"


class AISystemCriticality(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    very_high = "very_high"


class DataSensitivity(StrEnum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class Tenant(BaseModel):
    id: str
    name: str


class AISystemCreate(BaseModel):
    id: str = Field(..., examples=["ai-credit-scoring-v1"])
    name: str
    description: str
    business_unit: str
    risk_level: AISystemRiskLevel
    ai_act_category: AIActCategory
    gdpr_dpia_required: bool
    owner_email: str | None = None
    human_oversight_enabled: bool | None = None
    environment: str | None = None
    business_purpose: str | None = None
    criticality: AISystemCriticality = AISystemCriticality.medium
    data_sensitivity: DataSensitivity = DataSensitivity.internal


class AISystemUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    business_unit: str | None = None
    risk_level: AISystemRiskLevel | None = None
    ai_act_category: AIActCategory | None = None
    gdpr_dpia_required: bool | None = None
    owner_email: str | None = None
    human_oversight_enabled: bool | None = None
    environment: str | None = None
    business_purpose: str | None = None
    criticality: AISystemCriticality | None = None
    data_sensitivity: DataSensitivity | None = None

class AISystem(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str
    business_unit: str
    risk_level: AISystemRiskLevel
    ai_act_category: AIActCategory
    gdpr_dpia_required: bool
    owner_email: str | None = None
    human_oversight_enabled: bool | None = None
    environment: str | None = None
    business_purpose: str | None = None
    criticality: AISystemCriticality = AISystemCriticality.medium
    data_sensitivity: DataSensitivity = DataSensitivity.internal
    status: AISystemStatus = AISystemStatus.draft
    created_at_utc: datetime = Field(default_factory=lambda: datetime.utcnow())
    updated_at_utc: datetime = Field(default_factory=lambda: datetime.utcnow())


class AISystemRiskSummary(BaseModel):
    risk_level: AISystemRiskLevel
    count: int


class AISystemAIActSummary(BaseModel):
    ai_act_category: AIActCategory
    count: int


class AISystemCriticalitySummary(BaseModel):
    criticality: AISystemCriticality
    count: int


class AISystemDataSensitivitySummary(BaseModel):
    data_sensitivity: DataSensitivity
    count: int


class AISystemComplianceReport(BaseModel):
    tenant_id: str
    total_systems: int
    by_risk_level: list[AISystemRiskSummary]
    by_ai_act_category: list[AISystemAIActSummary]
    by_criticality: list[AISystemCriticalitySummary]
    by_data_sensitivity: list[AISystemDataSensitivitySummary]
