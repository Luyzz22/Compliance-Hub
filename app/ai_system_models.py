from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, EmailStr, Field


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
    owner_email: EmailStr
    criticality: AISystemCriticality = AISystemCriticality.medium
    data_sensitivity: DataSensitivity = DataSensitivity.internal


class AISystem(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str
    business_unit: str
    risk_level: AISystemRiskLevel
    ai_act_category: AIActCategory
    gdpr_dpia_required: bool
    owner_email: EmailStr
    criticality: AISystemCriticality = AISystemCriticality.medium
    data_sensitivity: DataSensitivity = DataSensitivity.internal
    status: AISystemStatus = AISystemStatus.draft
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))

