from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class PolicyScope(StrEnum):
    ai_system = "ai_system"
    tenant = "tenant"


class NormReference(BaseModel):
    framework: str = Field(..., examples=["EU_AI_ACT", "ISO_42001", "ISO_27001", "NIS2"])
    reference: str = Field(..., examples=["Art. 9", "A.8.1", "Annex III-2"])


class PolicyRuleCondition(BaseModel):
    field_path: str
    expected: Any
    operator: str = "equals"


class PolicyRule(BaseModel):
    id: str
    policy_id: str | None = None
    tenant_id: str | None = None
    name: str | None = None
    description: str
    severity: Severity
    message: str
    norm_references: list[NormReference] = []
    conditions: list[PolicyRuleCondition]


class Policy(BaseModel):
    id: str
    tenant_id: str | None = None
    name: str
    description: str | None = None
    active: bool = True
    scope: PolicyScope = PolicyScope.ai_system
    rules: list[PolicyRule] = []


class Violation(BaseModel):
    id: str | None = None
    tenant_id: str
    ai_system_id: str
    rule_id: str
    message: str
    description: str | None = None
    severity: Severity | None = None
    created_at: datetime | None = None


# Backwards-compat aliases for existing repository code
Rule = PolicyRule


class RuleConditionType(StrEnum):
    equals = "equals"
    high_risk_requires_dpia = "high_risk_requires_dpia"
    high_criticality_requires_owner_email = "high_criticality_requires_owner_email"

