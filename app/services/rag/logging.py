"""Structured audit logging for RAG query events.

Logs retrieval metadata without PII—only query hashes, doc_ids, scores,
and configuration parameters.  Designed to feed the AI Act Evidence API
and observability dashboards.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.rag.corpus import RetrievalResponse
from app.services.rag.evidence_store import record_event

logger = logging.getLogger("compliancehub.rag.audit")


@dataclass
class RAGQueryEvent:
    timestamp_epoch: float = field(default_factory=time.time)
    query_hash: str = ""
    tenant_id: str = ""
    retrieval_mode: str = ""
    alpha_used: float = 0.0
    confidence_level: str = ""
    confidence_score: float = 0.0
    top_doc_ids: list[str] = field(default_factory=list)
    top_scores: list[float] = field(default_factory=list)
    top_bm25_scores: list[float] = field(default_factory=list)
    top_dense_scores: list[float] = field(default_factory=list)
    top_rescue_sources: list[str] = field(default_factory=list)
    has_tenant_guidance: bool = False
    result_count: int = 0
    bm25_top_doc_id: str = ""
    hybrid_changed_top_doc: bool = False
    """True when hybrid reranking promoted a different doc than BM25 alone."""
    agent_action: str = ""
    """If called from an agent graph, records the decision (e.g. 'synthesize', 'escalate')."""
    extra: dict[str, Any] = field(default_factory=dict)


def _top_doc_primary_source(retrieval_mode: str, hybrid_changed: bool) -> str:
    if retrieval_mode == "bm25" or not hybrid_changed:
        return "bm25"
    return "dense_rescue"


def _evidence_payload_from_event(
    event: RAGQueryEvent,
    *,
    query_sha256: str,
    decline_reason: str | None,
    trace_id: str | None,
) -> dict[str, Any]:
    scores_summary: dict[str, float] = {}
    if event.top_scores:
        scores_summary = {
            "top_combined": event.top_scores[0],
            "top_bm25": event.top_bm25_scores[0] if event.top_bm25_scores else 0.0,
            "top_dense": event.top_dense_scores[0] if event.top_dense_scores else 0.0,
        }
    citations = [{"doc_id": doc_id} for doc_id in event.top_doc_ids[:5]]
    return {
        "event_type": "rag_query",
        "tenant_id": event.tenant_id,
        "query_sha256": query_sha256,
        "retrieval_mode": event.retrieval_mode,
        "top_doc_ids": event.top_doc_ids,
        "scores_summary": scores_summary,
        "confidence_level": event.confidence_level or None,
        "confidence_score": event.confidence_score,
        "citations": citations,
        "tenant_guidance_matched": event.has_tenant_guidance,
        "hybrid_alpha": event.alpha_used if event.retrieval_mode == "hybrid" else None,
        "top_doc_primary_source": _top_doc_primary_source(
            event.retrieval_mode, event.hybrid_changed_top_doc
        ),
        "hybrid_differs_from_bm25_top": event.hybrid_changed_top_doc,
        "decline_reason": decline_reason,
        "trace_id": trace_id,
    }


def log_rag_query_event(
    response: RetrievalResponse,
    tenant_id: str = "",
    agent_action: str = "",
    extra: dict[str, Any] | None = None,
    *,
    query_text: str | None = None,
    decline_reason: str | None = None,
    trace_id: str | None = None,
    persist_evidence: bool = True,
) -> RAGQueryEvent:
    """Build and emit a structured RAG audit event (no PII).

    Returns the event for callers that want to persist it additionally
    (e.g. to the AI Act Evidence API).
    """
    results = response.results
    bm25_top = ""
    hybrid_changed = False
    if results:
        bm25_sorted = sorted(results, key=lambda r: r.bm25_score, reverse=True)
        bm25_top = bm25_sorted[0].doc.doc_id if bm25_sorted else ""
        if results[0].doc.doc_id != bm25_top:
            hybrid_changed = True

    event = RAGQueryEvent(
        query_hash=response.query_hash,
        tenant_id=tenant_id,
        retrieval_mode=response.retrieval_mode,
        alpha_used=response.alpha_used,
        confidence_level=response.confidence_level,
        confidence_score=response.confidence_score,
        top_doc_ids=[r.doc.doc_id for r in results],
        top_scores=[round(r.score, 4) for r in results],
        top_bm25_scores=[round(r.bm25_score, 4) for r in results],
        top_dense_scores=[round(r.dense_score, 4) for r in results],
        top_rescue_sources=[r.rescue_source for r in results],
        has_tenant_guidance=response.has_tenant_guidance,
        result_count=len(results),
        bm25_top_doc_id=bm25_top,
        hybrid_changed_top_doc=hybrid_changed,
        agent_action=agent_action,
        extra=extra or {},
    )

    logger.info(
        "rag_query_event",
        extra={"rag_event": asdict(event)},
    )

    if persist_evidence:
        qsha = (
            hashlib.sha256(query_text.encode()).hexdigest()
            if query_text
            else response.query_hash
        )
        record_event(
            _evidence_payload_from_event(
                event,
                query_sha256=qsha,
                decline_reason=decline_reason,
                trace_id=trace_id,
            )
        )
    return event


def log_advisor_agent_event(
    *,
    tenant_id: str,
    decision: str,
    reason: str | None = None,
    intent: str | None = None,
    trace_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event_type": "advisor_agent",
        "tenant_id": tenant_id,
        "decision": decision,
        "reason": reason,
        "intent": intent,
        "trace_id": trace_id,
    }
    if extra:
        payload["extra"] = extra
    logger.info(
        "advisor_agent_event",
        extra={"advisor_agent": payload},
    )
    record_event(payload)
    return payload
