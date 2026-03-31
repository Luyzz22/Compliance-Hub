"""Stable JSON contracts for AI evidence list/detail/export (frontend-ready)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AiEvidenceEventType = Literal[
    "rag_query",
    "board_report_workflow_started",
    "board_report_completed",
    "llm_contract_violation",
    "llm_guardrail_block",
]

AiEvidenceSource = Literal["rag", "temporal", "llm"]


class AiEvidenceEventListItem(BaseModel):
    """Single row for list + export (no prompt/answer bodies)."""

    event_id: str
    timestamp: datetime
    event_type: str
    tenant_id: str
    user_role: str = Field(
        description=("OPA-Rolle oder technischer Actor-Typ (z. B. advisor, api_key)."),
    )
    source: AiEvidenceSource
    summary_de: str = Field(description="Kurzbeschreibung für Compliance/Revision (Deutsch).")
    confidence_level: str | None = None
    purpose: str | None = Field(
        default=None,
        description=("Zweck der KI-Nutzung (Transparenz), z. B. regulatory_qa, board_reporting."),
    )
    system_id: str | None = Field(
        default=None,
        description="Bezogenes KI-System, falls aus Metadaten ableitbar.",
    )
    risk_category: str | None = Field(
        default=None,
        description="Risikokategorie / Kontext (z. B. high_risk_governance).",
    )
    input_source: Literal["human", "system"] | None = Field(
        default=None,
        description="Ob menschliche Eingabe oder Systemtrigger vorlag.",
    )
    output_target: str | None = Field(
        default=None,
        description="Zielgruppe des Outputs (z. B. advisor, board_report).",
    )


class AiEvidenceRagScoreAuditRow(BaseModel):
    doc_id: str
    bm25_score: float = 0.0
    embedding_score: float = 0.0
    combined_score: float = 0.0
    rag_scope: str = ""
    is_tenant_guidance: bool = False


class AiEvidenceRagDetailSection(BaseModel):
    query_sha256: str | None = None
    citation_doc_ids: list[str] = Field(default_factory=list)
    tenant_guidance_citation_count: int = 0
    confidence_level: str | None = None
    trace_id: str | None = None
    span_id: str | None = None
    citation_count: int = 0
    retrieval_mode: str | None = Field(
        default=None,
        description="bm25 oder hybrid (aus Audit-Metadaten).",
    )
    score_audit: list[AiEvidenceRagScoreAuditRow] = Field(
        default_factory=list,
        description="BM25-, Embedding- und kombinierte Scores je Treffer (Hybrid).",
    )


class AiEvidenceBoardReportWorkflowDetailSection(BaseModel):
    workflow_id: str
    task_queue: str | None = None
    status_hint: str | None = Field(
        default=None,
        description="Aus Audit-Aktion abgeleitet (z. B. started); kein Live-Temporal-Status.",
    )


class AiEvidenceBoardReportCompletedDetailSection(BaseModel):
    report_id: str
    temporal_workflow_id: str | None = None
    temporal_run_id: str | None = None
    audience_type: str
    activities_executed: list[str] = Field(
        default_factory=list,
        description=("Aus Payload abgeleitete Aktivitätsreihenfolge (ohne Roh-Inhalt)."),
    )
    title: str


class AiEvidenceLlmDetailSection(BaseModel):
    action_name: str | None = None
    task_type: str | None = None
    contract_schema: str | None = None
    error_class: str | None = None
    guardrail_flags: dict[str, str] | None = None


class AiEvidenceEventDetail(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: str
    tenant_id: str
    user_role: str
    source: AiEvidenceSource
    summary_de: str
    purpose: str | None = None
    system_id: str | None = None
    risk_category: str | None = None
    input_source: Literal["human", "system"] | None = None
    output_target: str | None = None
    rag: AiEvidenceRagDetailSection | None = None
    board_report_workflow: AiEvidenceBoardReportWorkflowDetailSection | None = None
    board_report_completed: AiEvidenceBoardReportCompletedDetailSection | None = None
    llm: AiEvidenceLlmDetailSection | None = None


class AiEvidenceEventListResponse(BaseModel):
    items: list[AiEvidenceEventListItem]
    total: int
    limit: int
    offset: int
