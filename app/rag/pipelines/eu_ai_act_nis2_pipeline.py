"""
EU AI Act / NIS2 / ISO 42001 advisor RAG — explicit execution graph (BM25 or hybrid).

Steps (auditable, no hidden lambdas):
  1. Retrieval — ``merged_bm25_retrieve`` (``COMPLIANCEHUB_ADVISOR_RAG_RETRIEVAL_MODE=bm25``)
     or ``hybrid_merged_retrieve`` + ``InMemoryEmbeddingRetriever`` (``mode=hybrid``).
  2. Quality gate — min BM25 score and/or hybrid combined + embedding rescue (see config).
  3. ``compute_confidence_level`` — heuristic from active score scale.
  4. ``build_eu_reg_rag_prompt`` — German prompt + source catalog.
  5. ``generate_eu_reg_rag_llm_output`` — ``safe_llm_call_sync`` + ``LlmCallContext``.

Haystack ``Pipeline`` is optional; the sequence is fixed in code so logs and tests hook each stage.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from haystack.dataclasses import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.rag.confidence import compute_confidence_level
from app.rag.embeddings.runtime import embed_query_for_hybrid, ensure_document_store_embeddings
from app.rag.generation import generate_eu_reg_rag_llm_output
from app.rag.haystack_config import (
    rag_advisor_retrieval_mode,
    rag_bm25_min_score,
    rag_confidence_gap_min,
    rag_confidence_high_score_min,
    rag_hybrid_confidence_gap_min,
    rag_hybrid_confidence_high_min,
    rag_hybrid_min_combined_score,
    rag_hybrid_rescue_embedding_min,
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
from app.rag.retrievers.hybrid_eu_ai_act import (
    HybridRetrievalPack,
    filter_documents_hybrid,
    hybrid_merged_retrieve,
)
from app.telemetry.tracing import record_event, start_span

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass
class EuRegRagPipelineResult:
    """Structured outcome for API mapping and tests."""

    structured: dict
    documents_for_prompt: list[Document]
    merged_documents: list[Document]
    merged_scores: list[float]
    confidence_level: str
    notes_de: str | None
    used_llm: bool
    retrieval_mode: str = "bm25"
    retrieval_hit_audit: list[dict[str, Any]] = field(default_factory=list)


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

    mode = rag_advisor_retrieval_mode()
    hybrid_pack_bm25: dict[str, float] | None = None
    hybrid_pack_emb: dict[str, float] | None = None
    hybrid_pack: HybridRetrievalPack | None = None

    with start_span(
        "rag.retrieval",
        tenant_id=tenant_id,
        user_role=user_role,
        top_k_effective=rag_merged_top_k(),
    ):
        if mode == "hybrid":
            ensure_document_store_embeddings(document_store)
            q_emb = embed_query_for_hybrid(q)
            hybrid_pack = hybrid_merged_retrieve(
                document_store,
                query=q,
                tenant_id=tenant_id,
                query_embedding=q_emb,
            )
            merged = hybrid_pack.documents
            merged_scores, merged_ids = documents_scores_and_ids(merged)
            hybrid_pack_bm25 = hybrid_pack.bm25_scores
            hybrid_pack_emb = hybrid_pack.embedding_scores
            retrieval_extra: dict = {
                "merged_hits": len(merged),
                "retrieval_mode": "hybrid",
                "hybrid_alpha": hybrid_pack.alpha,
                "retrieval_hit_audit": hybrid_pack.hit_audit[:20],
            }
        else:
            merged = merged_bm25_retrieve(document_store, query=q, tenant_id=tenant_id)
            merged_scores, merged_ids = documents_scores_and_ids(merged)
            retrieval_extra = {"merged_hits": len(merged), "retrieval_mode": "bm25"}

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
            extra=retrieval_extra,
        )

        min_s = rag_bm25_min_score()
        if mode == "hybrid" and hybrid_pack_bm25 is not None and hybrid_pack_emb is not None:
            filtered = filter_documents_hybrid(
                merged,
                bm25_scores=hybrid_pack_bm25,
                embedding_scores=hybrid_pack_emb,
                min_bm25=min_s,
                min_combined=rag_hybrid_min_combined_score(),
                rescue_embedding_min=rag_hybrid_rescue_embedding_min(),
            )
            h_min = rag_hybrid_min_combined_score()
            h_high = rag_hybrid_confidence_high_min()
            h_gap = rag_hybrid_confidence_gap_min()
        else:
            filtered = filter_documents_by_min_score(merged, min_s)
            h_min = min_s
            h_high = rag_confidence_high_score_min()
            h_gap = rag_confidence_gap_min()

        conf_scores = documents_scores_and_ids(filtered)[0] if filtered else merged_scores
        confidence_level, conf_notes = compute_confidence_level(
            conf_scores,
            min_score_for_answer=h_min,
            high_score_min=h_high,
            score_gap_min=h_gap,
        )

        if not filtered:
            record_event("rag.generation_skipped", reason="no_hits_above_threshold")
            payload = EuRegRagLlmOutput(
                answer_de=_FALLBACK_NO_HIT_DE,
                citations=[],
            ).model_dump(mode="json")
            t_end = time.perf_counter()
            resp_extra: dict[str, Any] = {
                "used_llm": False,
                "filtered_hits": 0,
                "retrieval_mode": mode,
            }
            if hybrid_pack is not None:
                resp_extra["hybrid_alpha"] = hybrid_pack.alpha
                resp_extra["retrieval_hit_audit"] = hybrid_pack.hit_audit[:20]
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
                extra=resp_extra,
            )
            return EuRegRagPipelineResult(
                structured=payload,
                documents_for_prompt=[],
                merged_documents=merged,
                merged_scores=merged_scores,
                confidence_level="low",
                notes_de=conf_notes,
                used_llm=False,
                retrieval_mode=mode,
                retrieval_hit_audit=list(hybrid_pack.hit_audit[:20]) if hybrid_pack else [],
            )

    with start_span("rag.generation", tenant_id=tenant_id, user_role=user_role):
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

        resp_extra_ok: dict[str, Any] = {
            "used_llm": True,
            "filtered_hits": len(filtered),
            "retrieval_mode": mode,
        }
        if hybrid_pack is not None:
            resp_extra_ok["hybrid_alpha"] = hybrid_pack.alpha
            resp_extra_ok["retrieval_hit_audit"] = hybrid_pack.hit_audit[:20]
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
            extra=resp_extra_ok,
        )

        return EuRegRagPipelineResult(
            structured=parsed.model_dump(mode="json"),
            documents_for_prompt=filtered,
            merged_documents=merged,
            merged_scores=merged_scores,
            confidence_level=confidence_level,
            notes_de=notes,
            used_llm=True,
            retrieval_mode=mode,
            retrieval_hit_audit=list(hybrid_pack.hit_audit[:20]) if hybrid_pack else [],
        )
