"""Pydantic models: EU AI Act / NIS2 / ISO 42001 advisor RAG API + LLM contract."""

from __future__ import annotations

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
    doc_id: str
    source: str
    section: str


class EuAiActNis2RagResponse(BaseModel):
    answer_de: str
    citations: list[EuAiActNis2RagCitation] = Field(
        default_factory=list,
        description="Bis zu drei wichtigste Belege aus dem Kurpus.",
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
