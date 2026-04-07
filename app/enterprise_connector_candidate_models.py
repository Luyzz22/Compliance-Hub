from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.enterprise_integration_blueprint_models import SourceSystemType


class ConnectorCandidatePriority(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"
    not_now = "not_now"


class ImplementationComplexityBand(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class EnterpriseConnectorCandidateRow(BaseModel):
    tenant_id: str
    connector_type: SourceSystemType
    readiness_score: int = Field(ge=0, le=100)
    blocker_score: int = Field(ge=0, le=100)
    strategic_value_score: int = Field(ge=0, le=100)
    compliance_impact_score: int = Field(ge=0, le=100)
    estimated_implementation_complexity: int = Field(ge=0, le=100)
    complexity_band: ImplementationComplexityBand
    recommended_priority: ConnectorCandidatePriority
    rationale_summary_de: str
    rationale_factors_de: list[str] = Field(default_factory=list)
    score_total: int = Field(ge=0, le=100)


class ConnectorScoringWeights(BaseModel):
    readiness_weight: int = 35
    blocker_weight: int = 20
    strategic_value_weight: int = 25
    compliance_impact_weight: int = 20


class EnterpriseConnectorCandidatesResponse(BaseModel):
    tenant_id: str
    generated_at_utc: datetime
    scoring_weights: ConnectorScoringWeights
    candidate_rows: list[EnterpriseConnectorCandidateRow]
    top_priorities: list[EnterpriseConnectorCandidateRow]
    grouped_priorities_by_connector_type: dict[str, list[EnterpriseConnectorCandidateRow]]
    markdown_de: str | None = None
