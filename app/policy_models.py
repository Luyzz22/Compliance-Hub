from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RuleConditionType(StrEnum):
    high_risk_requires_dpia = "high_risk_requires_dpia"
    high_criticality_requires_owner_email = "high_criticality_requires_owner_email"


class Policy(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str | None = None
    active: bool = True


class Rule(BaseModel):
    id: str
    policy_id: str
    tenant_id: str
    name: str
    description: str | None = None
    condition_type: RuleConditionType


class Violation(BaseModel):
    id: str
    tenant_id: str
    ai_system_id: str
    rule_id: str
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.utcnow())
