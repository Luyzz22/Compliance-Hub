"""Request/response for KPI- und Alert-Erklärungen (LLM, nicht persistiert)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExplainTenantContext(BaseModel):
    industry: str | None = Field(default=None, max_length=128)
    nis2_scope: str | None = Field(default=None, max_length=64)
    high_risk_systems_count: int | None = Field(default=None, ge=0)


class ExplainRequest(BaseModel):
    kpi_key: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="z.B. nis2_incident_readiness_ratio, eu_ai_act_readiness, board_alert:*",
    )
    current_value: float | None = Field(
        default=None,
        description="Istwert; Einheit über value_is_percent (0–1 vs. 0–100).",
    )
    value_is_percent: bool = Field(
        default=False,
        description="Wenn true: current_value ist 0–100, sonst 0–1.",
    )
    alert_key: str | None = Field(default=None, max_length=160)
    threshold_warning: float | None = None
    threshold_critical: float | None = None
    tenant_context: ExplainTenantContext | None = None


class ExplainResponse(BaseModel):
    title: str = Field(..., max_length=500)
    summary: str = Field(..., max_length=4000)
    why_it_matters: list[str] = Field(default_factory=list, max_length=12)
    suggested_actions: list[str] = Field(default_factory=list, max_length=16)
