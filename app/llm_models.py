"""Domain model for LLM routing: task types, providers, tenant policies, responses."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class LLMTaskType(StrEnum):
    """Use-case categories for model selection and governance."""

    LEGAL_REASONING = "legal_reasoning"
    STRUCTURED_OUTPUT = "structured_output"
    CLASSIFICATION_TAGGING = "classification_tagging"
    CHAT_ASSISTANT = "chat_assistant"
    EMBEDDING_RETRIEVAL = "embedding_retrieval"
    ON_PREM_SENSITIVE = "on_prem_sensitive"
    KPI_SUGGESTION_ASSIST = "kpi_suggestion_assist"
    EXPLAIN_KPI_ALERT = "explain_kpi_alert"
    ACTION_DRAFT_GENERATION = "action_draft_generation"
    CROSS_REGULATION_GAP_ASSIST = "cross_regulation_gap_assist"
    AI_COMPLIANCE_BOARD_REPORT = "ai_compliance_board_report"
    ADVISOR_GOVERNANCE_SNAPSHOT = "advisor_governance_snapshot"


class LLMProvider(StrEnum):
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    LLAMA = "llama"


class DataResidencyPolicy(StrEnum):
    """
    Where tenant data may be processed by model APIs.

    Assumptions (documented in docs/llm-routing.md):
    - OPENAI / GEMINI vendor APIs are treated as US-cloud for routing unless you deploy
      EU data residency offerings and set COMPLIANCEHUB_LLM_US_CLOUD_OK=true.
    - Anthropic (CLAUDE) may process in multiple regions; for strict EU_ONLY we only allow
      CLAUDE if COMPLIANCEHUB_LLM_ASSUME_CLAUDE_EU=true (operator attestation).
    - LLAMA is the default path for EU_ONLY / no public API when an on-prem URL is set.
    """

    US_CLOUD_ALLOWED = "us_cloud_allowed"
    EU_ONLY = "eu_only"


class PublicApiPolicy(StrEnum):
    """Whether calls may leave the tenant-controlled network to public SaaS LLM APIs."""

    PUBLIC_API_ALLOWED = "public_api_allowed"
    ON_PREM_ONLY = "on_prem_only"


class CostSensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LatencySensitivity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TenantLLMPolicy(BaseModel):
    """Per-tenant LLM routing and compliance constraints."""

    tenant_id: str = Field(..., min_length=1)
    allowed_providers: list[LLMProvider] = Field(
        default_factory=lambda: list(LLMProvider),
        description="Providers permitted for this tenant after residency/public-API filters.",
    )
    default_provider_by_task: dict[LLMTaskType, LLMProvider] = Field(default_factory=dict)
    require_on_prem_for_sensitive: bool = Field(
        default=False,
        description="If true, ON_PREM_SENSITIVE must use on-prem stack (LLAMA).",
    )
    cost_sensitivity: CostSensitivity = CostSensitivity.MEDIUM
    latency_sensitivity: LatencySensitivity = LatencySensitivity.MEDIUM
    data_residency: DataResidencyPolicy = DataResidencyPolicy.US_CLOUD_ALLOWED
    public_api_policy: PublicApiPolicy = PublicApiPolicy.PUBLIC_API_ALLOWED

    @field_validator("default_provider_by_task", mode="before")
    @classmethod
    def _coerce_task_provider_keys(
        cls,
        v: Any,
    ) -> dict[LLMTaskType, LLMProvider]:
        if not isinstance(v, dict):
            return {}
        out: dict[LLMTaskType, LLMProvider] = {}
        for k, val in v.items():
            kt = LLMTaskType(str(k)) if not isinstance(k, LLMTaskType) else k
            pv = LLMProvider(str(val)) if not isinstance(val, LLMProvider) else val
            out[kt] = pv
        return out

    @field_validator("allowed_providers", mode="before")
    @classmethod
    def _coerce_providers(cls, v: Any) -> list[LLMProvider]:
        if v is None:
            return list(LLMProvider)
        if not isinstance(v, list):
            return list(LLMProvider)
        return [LLMProvider(str(p)) if not isinstance(p, LLMProvider) else p for p in v]


class LLMResponse(BaseModel):
    """Provider-agnostic completion result (no persistence of raw content in router logs)."""

    text: str
    provider: LLMProvider
    model_id: str
    input_tokens_est: int = Field(ge=0, default=0)
    output_tokens_est: int = Field(ge=0, default=0)


class LLMCallMetadataRecord(BaseModel):
    """Metadata persisted per router invocation (no prompt/response body)."""

    tenant_id: str
    task_type: LLMTaskType
    provider: LLMProvider
    model_id: str
    prompt_length: int = Field(ge=0)
    response_length: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    estimated_input_tokens: int = Field(ge=0)
    estimated_output_tokens: int = Field(ge=0)
