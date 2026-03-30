"""
EU AI Act / NIS2 / ISO 42001 advisor RAG — explicit execution graph (BM25 pilot).

Steps (auditable, no hidden lambdas):
  1. ``merged_bm25_retrieve`` — global corpus + optional tenant guidance (metadata filters).
  2. ``filter_documents_by_min_score`` — quality gate.
  3. ``compute_confidence_level`` — heuristic label from scores.
  4. ``build_eu_reg_rag_prompt`` — German prompt + source catalog.
  5. ``generate_eu_reg_rag_llm_output`` — ``safe_llm_call_sync`` + ``LlmCallContext``.

Haystack ``Pipeline`` is not required for this wave; the sequence above is fixed in code
so logs and tests can hook each stage.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from haystack.dataclasses import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.rag.confidence import compute_confidence_level
from app.rag.generation import generate_eu_reg_rag_llm_output
from app.rag.haystack_config import (
    rag_bm25_min_score,
    rag_confidence_gap_min,
    rag_confidence_high_score_min,
    rag_merged_top_k,
)
from app.rag.models import EuRegRagLlmOutput
from app.rag.observability import (
    log_rag_query_event,
    query_sha256_hex,
    redacted_query_preview,
)
from app.rag.prompting import build_eu_reg_rag_prompt
from app.rag.retrieval import (
    documents_scores_and_ids,
    filter_documents_by_min_score,
    merged_bm25_retrieve,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(frozen=True)
class EuRegRagPipelineResult:
    """Structured outcome for API mapping and tests."""

    structured: dict
    documents_for_prompt: list[Document]
    merged_documents: list[Document]
    merged_scores: list[float]
    confidence_level: str
    notes_de: str | None
    used_llm: bool


_FALLBACK_NO_HIT_DE = (
    "Für diese Frage liegen uns in der EU-AI-Act/NIS2-Wissensbasis aktuell keine eindeutigen "
    "Textstellen vor. Bitte ziehen Sie bei Bedarf eine menschliche Fachexpertin bzw. einen "
    "Fachexperten hinzu."
)


def run_eu_ai_act_nis2_pipeline(
    *,
    question_de: str,
    tenant_id: str,
    user_role: str,
    document_store: InMemoryDocumentStore,
    session: Session | None = None,
    advisor_id: str | None = None,
) -> EuRegRagPipelineResult:
    t0 = time.perf_counter()
    q = question_de.strip()
    q_hash = query_sha256_hex(q)
    q_prev = redacted_query_preview(q)
    q_len = len(q)

    merged = merged_bm25_retrieve(document_store, query=q, tenant_id=tenant_id)
    merged_scores, merged_ids = documents_scores_and_ids(merged)
    t_after_retrieval = time.perf_counter()
    latency_retrieval_ms = (t_after_retrieval - t0) * 1000.0

    log_rag_query_event(
        phase="retrieval_complete",
        tenant_id=tenant_id,
        user_role=user_role,
        advisor_id=advisor_id,
        query_sha256=q_hash,
        query_length_chars=q_len,
        query_redacted_preview=q_prev,
        top_k_effective=rag_merged_top_k(),
        retrieved_doc_ids=merged_ids,
        retrieval_scores=merged_scores,
        latency_ms_retrieval=latency_retrieval_ms,
        extra={"merged_hits": len(merged)},
    )

    min_s = rag_bm25_min_score()
    filtered = filter_documents_by_min_score(merged, min_s)
    conf_scores = documents_scores_and_ids(filtered)[0] if filtered else merged_scores
    confidence_level, conf_notes = compute_confidence_level(
        conf_scores,
        min_score_for_answer=min_s,
        high_score_min=rag_confidence_high_score_min(),
        score_gap_min=rag_confidence_gap_min(),
    )

    if not filtered:
        payload = EuRegRagLlmOutput(
            answer_de=_FALLBACK_NO_HIT_DE,
            citations=[],
        ).model_dump(mode="json")
        t_end = time.perf_counter()
        log_rag_query_event(
            phase="response_complete",
            tenant_id=tenant_id,
            user_role=user_role,
            advisor_id=advisor_id,
            query_sha256=q_hash,
            query_length_chars=q_len,
            query_redacted_preview=q_prev,
            top_k_effective=rag_merged_top_k(),
            retrieved_doc_ids=merged_ids,
            retrieval_scores=merged_scores,
            latency_ms_retrieval=latency_retrieval_ms,
            latency_ms_llm=0.0,
            latency_ms_total=(t_end - t0) * 1000.0,
            confidence_level="low",
            extra={"used_llm": False, "filtered_hits": 0},
        )
        return EuRegRagPipelineResult(
            structured=payload,
            documents_for_prompt=[],
            merged_documents=merged,
            merged_scores=merged_scores,
            confidence_level="low",
            notes_de=conf_notes,
            used_llm=False,
        )

    prompt = build_eu_reg_rag_prompt(q, filtered)
    t_before_llm = time.perf_counter()
    parsed = generate_eu_reg_rag_llm_output(
        prompt,
        tenant_id=tenant_id,
        user_role=user_role,
        session=session,
    )
    t_end = time.perf_counter()
    latency_llm_ms = (t_end - t_before_llm) * 1000.0
    notes = conf_notes if confidence_level in ("low", "medium") else None

    log_rag_query_event(
        phase="response_complete",
        tenant_id=tenant_id,
        user_role=user_role,
        advisor_id=advisor_id,
        query_sha256=q_hash,
        query_length_chars=q_len,
        query_redacted_preview=q_prev,
        top_k_effective=rag_merged_top_k(),
        retrieved_doc_ids=merged_ids,
        retrieval_scores=merged_scores,
        latency_ms_retrieval=latency_retrieval_ms,
        latency_ms_llm=latency_llm_ms,
        latency_ms_total=(t_end - t0) * 1000.0,
        confidence_level=confidence_level,
        extra={"used_llm": True, "filtered_hits": len(filtered)},
    )

    return EuRegRagPipelineResult(
        structured=parsed.model_dump(mode="json"),
        documents_for_prompt=filtered,
        merged_documents=merged,
        merged_scores=merged_scores,
        confidence_level=confidence_level,
        notes_de=notes,
        used_llm=True,
    )
