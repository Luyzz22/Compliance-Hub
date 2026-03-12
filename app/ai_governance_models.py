from __future__ import annotations

from pydantic import BaseModel, Field


class AIGovernanceKpiSummary(BaseModel):
    tenant_id: str
    governance_maturity_score: float = Field(ge=0.0, le=1.0)
    ai_systems_with_owner: int
    ai_systems_total: int
    high_risk_with_dpia: int
    high_risk_total: int
    policy_violations_open: int
    audit_events_last_30_days: int
    has_documented_ai_policy: bool = False
    has_ai_risk_register: bool = False
