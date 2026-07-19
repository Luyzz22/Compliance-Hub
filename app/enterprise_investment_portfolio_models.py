from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.enterprise_integration_blueprint_models import SourceSystemType


class InvestmentDecision(StrEnum):
    fund_now = "fund_now"
    sequence = "sequence"
    validate = "validate"
    hold = "hold"


class InvestmentEnvelopeBand(StrEnum):
    small = "small"
    medium = "medium"
    large = "large"


class TimeToValueBand(StrEnum):
    near_term = "near_term"
    mid_term = "mid_term"
    long_term = "long_term"


class InvestmentPortfolioWeights(BaseModel):
    strategic_value_weight: int = 30
    risk_reduction_weight: int = 30
    execution_confidence_weight: int = 25
    capital_efficiency_weight: int = 15


class EnterpriseInvestmentInitiative(BaseModel):
    initiative_id: str = Field(..., min_length=1, max_length=160)
    tenant_id: str = Field(..., min_length=1, max_length=255)
    connector_type: SourceSystemType
    initiative_name_de: str = Field(..., min_length=1, max_length=255)
    baseline_rank: int = Field(ge=1)
    recommended_decision: InvestmentDecision
    investment_envelope_band: InvestmentEnvelopeBand
    time_to_value_band: TimeToValueBand
    strategic_value_score: int = Field(ge=0, le=100)
    risk_reduction_score: int = Field(ge=0, le=100)
    execution_confidence_score: int = Field(ge=0, le=100)
    capital_efficiency_score: int = Field(ge=0, le=100)
    blocker_score: int = Field(ge=0, le=100)
    portfolio_score: int = Field(ge=0, le=100)
    decision_rationale_de: str = Field(..., min_length=1, max_length=1000)
    funding_preconditions_de: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    requires_finance_input: bool = True
    is_financial_estimate: bool = False


class InvestmentPortfolioSummary(BaseModel):
    total_initiatives: int = 0
    fund_now_count: int = 0
    sequence_count: int = 0
    validate_count: int = 0
    hold_count: int = 0
    large_envelope_count: int = 0
    missing_finance_inputs: int = 0
    top_recommendation_de: str | None = None


class EnterpriseInvestmentPortfolioResponse(BaseModel):
    tenant_id: str
    generated_at_utc: datetime
    baseline_weights: InvestmentPortfolioWeights
    summary: InvestmentPortfolioSummary
    initiatives: list[EnterpriseInvestmentInitiative]
    assumptions_de: list[str] = Field(default_factory=list)
    markdown_de: str | None = None
