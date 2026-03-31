"""Pydantic models: EU AI Act / NIS2 / ISO 42001 advisor RAG API + LLM contract."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EuAiActNis2RagRequest(BaseModel):
    question_de: str = Field(
        min_length=3,
        max_length=4000,
        description="Beraterfrage auf Deutsch zu EU AI Act, NIS2 oder ISO 42001.",
    )
    tenant_id: str = Field(min_length=1, description="Mandanten-Kontext für OPA/LLM/Audit.")
    context: dict[str, str] | None = Field(
        default=None,
        description="Optionale Zusatzmetadaten (nicht an Retriever übergeben, nur Logging).",
    )


class EuAiActNis2RagCitation(BaseModel):
    """Belegzeile; ältere Clients nutzen weiter ``doc_id``/``source``/``section``."""

    doc_id: str = Field(description="Stabile Chunk-ID (Haystack Document.id).")
    source_id: str = Field(
        default="",
        description="Identisch mit doc_id, falls nicht anders vergeben.",
    )
    title: str = Field(default="", description="Kurztitel, typisch Abschnittsüberschrift.")
    section: str
    source: str = Field(description="Quellenbezeichnung / Dateiname.")
    is_tenant_specific: bool = Field(
        default=False,
        description="True bei Mandanten-Leitfaden (tenant_guidance), sonst globaler Kurpus.",
    )


class RagRetrievalHitAuditRow(BaseModel):
    """Per-document retrieval scores for audits (hybrid mode); no raw text."""

    doc_id: str
    bm25_score: float = 0.0
    embedding_score: float = 0.0
    combined_score: float = 0.0
    rag_scope: str = ""
    is_tenant_guidance: bool = False


class EuAiActNis2RagResponse(BaseModel):
    answer_de: str
    citations: list[EuAiActNis2RagCitation] = Field(
        default_factory=list,
        description="Bis zu drei wichtigste Belege aus dem Kurpus.",
    )
    confidence_level: Literal["high", "medium", "low"] = Field(
        description="Heuristik aus BM25- bzw. kombinierten Hybrid-Scores (keine Rechtssicherheit).",
    )
    notes_de: str | None = Field(
        default=None,
        description="Hinweis bei niedriger/mittlerer Konfidenz oder fehlenden Treffern.",
    )
    retrieval_mode: Literal["bm25", "hybrid"] | None = Field(
        default=None,
        description="Aktiver Retriever: bm25 oder hybrid (BM25 + Embeddings).",
    )
    retrieval_hit_audit: list[RagRetrievalHitAuditRow] | None = Field(
        default=None,
        description=(
            "Top-Treffer mit BM25-, Embedding- und kombiniertem Score (nur hybrid, Metadaten)."
        ),
    )


class EuRegRagLlmCitation(BaseModel):
    doc_id: str = Field(max_length=128)
    source: str = Field(max_length=256)
    section: str = Field(max_length=256)


class EuRegRagLlmOutput(BaseModel):
    """Structured LLM output (safe_llm_call / JSON mode)."""

    answer_de: str = Field(max_length=16000)
    citations: list[EuRegRagLlmCitation] = Field(
        default_factory=list,
        description="Zitierte doc_id-Werte müssen exakt aus dem Katalog stammen (max. 5).",
    )
