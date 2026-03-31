from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RagEvidenceStoredEvent(BaseModel):
    """AI Act evidence row for RAG (no raw query text)."""

    model_config = ConfigDict(extra="ignore")

    recorded_at: str
    event_type: Literal["rag_query"] = "rag_query"
    tenant_id: str
    query_sha256: str
    retrieval_mode: str
    top_doc_ids: list[str] = Field(default_factory=list)
    scores_summary: dict[str, Any] = Field(default_factory=dict)
    confidence_level: str | None = None
    confidence_score: float | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    tenant_guidance_matched: bool | None = None
    hybrid_alpha: float | None = None
    top_doc_primary_source: str | None = None
    hybrid_differs_from_bm25_top: bool | None = None
    decline_reason: str | None = None
    trace_id: str | None = None


class AdvisorAgentEvidenceStoredEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    recorded_at: str
    event_type: Literal["advisor_agent"] = "advisor_agent"
    tenant_id: str
    decision: str
    reason: str | None = None
    intent: str | None = None
    trace_id: str | None = None


class RagRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=8000)
    retrieval_mode: Literal["bm25", "hybrid"] = "hybrid"
    k: int = Field(default=8, ge=1, le=50)
    trace_id: str | None = None
    tenant_expects_guidance: bool = False


class RagRetrieveResponse(BaseModel):
    """Retrieval-only response: hashes and scores only (no echo of query text by default)."""

    query_sha256: str
    retrieval_mode: str
    top_doc_ids: list[str]
    top_doc_primary_source: str | None
    hybrid_alpha: float | None
    hybrid_differs_from_bm25_top: bool
    confidence_level: str
    confidence_score: float
    decline_answer: bool
    decline_reason: str | None
    tenant_guidance_matched: bool
    scores_summary: dict[str, float]
    citations: list[dict[str, str]]


class RagEvidenceStatsResponse(BaseModel):
    tenant_id: str
    rag_events: int
    hybrid_differs_ratio: float | None
    dense_rescue_top_ratio: float | None
