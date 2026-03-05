from __future__ import annotations

from datetime import datetime, timezone
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
    status: AISystemStatus = AISystemStatus.draft
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
