"""
Hybrid retrieval for EU regulatory advisor RAG: BM25 + dense (explicit, auditable).

Combines normalized BM25 and dense similarity scores with a convex mix::

    combined = (1 - alpha) * norm_bm25 + alpha * norm_dense

where ``alpha`` = ``COMPLIANCEHUB_RAG_HYBRID_DENSE_ALPHA`` (default 0.5).

Per-hit ``bm25_score``, ``embedding_score``, and ``combined_score`` are emitted for logs and
the AI Evidence API (no raw text).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from typing import Any

from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.rag.haystack_config import (
    rag_hybrid_candidate_pool_k,
    rag_hybrid_dense_alpha,
    rag_merged_top_k,
)
from app.rag.retrieval import merged_bm25_retrieve, merged_embedding_retrieve

logger = logging.getLogger(__name__)


def _score_map(documents: list[Document]) -> dict[str, float]:
    out: dict[str, float] = {}
    for d in documents:
        did = str(d.id or "")
        if did:
            out[did] = float(getattr(d, "score", 0.0) or 0.0)
    return out


def _normalize_scores(raw: dict[str, float]) -> dict[str, float]:
    if not raw:
        return {}
    mx = max(raw.values())
    if mx <= 0:
        return {k: 0.0 for k in raw}
    return {k: v / mx for k, v in raw.items()}


def _doc_union(bm25_docs: list[Document], emb_docs: list[Document]) -> dict[str, Document]:
    by_id: dict[str, Document] = {}
    for d in bm25_docs:
        did = str(d.id or "")
        if did:
            by_id[did] = d
    for d in emb_docs:
        did = str(d.id or "")
        if did and did not in by_id:
            by_id[did] = d
    return by_id


@dataclass
class HybridRetrievalPack:
    """Outcome of hybrid retrieval for pipeline, logging, and audit metadata."""

    documents: list[Document]
    bm25_scores: dict[str, float] = field(default_factory=dict)
    embedding_scores: dict[str, float] = field(default_factory=dict)
    combined_scores: dict[str, float] = field(default_factory=dict)
    hit_audit: list[dict[str, Any]] = field(default_factory=list)
    retrieval_mode: str = "hybrid"
    alpha: float = 0.5


def hybrid_merged_retrieve(
    document_store: InMemoryDocumentStore,
    *,
    query: str,
    tenant_id: str,
    query_embedding: list[float],
    pool_k: int | None = None,
    alpha: float | None = None,
) -> HybridRetrievalPack:
    """
    Pool BM25 and dense candidates, convex-combine normalized scores, return top ``merged_top_k``.

    ``query_embedding`` must be provided (caller uses ``embed_query_for_hybrid`` or a test stub).
    """
    a = rag_hybrid_dense_alpha() if alpha is None else alpha
    pool = pool_k if pool_k is not None else rag_hybrid_candidate_pool_k()
    final_k = rag_merged_top_k()

    bm25_docs = merged_bm25_retrieve(
        document_store,
        query=query,
        tenant_id=tenant_id,
        merged_cap=pool,
    )
    emb_docs = merged_embedding_retrieve(
        document_store,
        query_embedding,
        tenant_id=tenant_id,
        merged_cap=pool,
    )

    bm25_raw = _score_map(bm25_docs)
    emb_raw = _score_map(emb_docs)
    bm25_n = _normalize_scores(bm25_raw)
    emb_n = _normalize_scores(emb_raw)
    all_ids = set(bm25_n) | set(emb_n)
    combined: dict[str, float] = {}
    for did in all_ids:
        b = bm25_n.get(did, 0.0)
        e = emb_n.get(did, 0.0)
        combined[did] = (1.0 - a) * b + a * e

    ranked_ids = sorted(combined.keys(), key=lambda i: combined[i], reverse=True)[:final_k]
    doc_by_id = _doc_union(bm25_docs, emb_docs)

    out_docs: list[Document] = []
    hit_audit: list[dict[str, Any]] = []
    for did in ranked_ids:
        base = doc_by_id.get(did)
        if base is None:
            continue
        cscore = combined[did]
        out_docs.append(replace(base, score=cscore))
        meta = base.meta or {}
        scope = str(meta.get("rag_scope", "") or "")
        hit_audit.append(
            {
                "doc_id": did,
                "bm25_score": round(bm25_raw.get(did, 0.0), 6),
                "embedding_score": round(emb_raw.get(did, 0.0), 6),
                "combined_score": round(cscore, 6),
                "rag_scope": scope,
                "is_tenant_guidance": scope == "tenant_guidance",
            },
        )

    logger.debug(
        "hybrid_retrieve tenant=%s pool=%s final=%s alpha=%s",
        tenant_id,
        pool,
        len(out_docs),
        a,
    )
    return HybridRetrievalPack(
        documents=out_docs,
        bm25_scores=bm25_raw,
        embedding_scores=emb_raw,
        combined_scores={k: combined[k] for k in ranked_ids if k in combined},
        hit_audit=hit_audit,
        retrieval_mode="hybrid",
        alpha=a,
    )


def filter_documents_hybrid(
    documents: list[Document],
    *,
    bm25_scores: dict[str, float],
    embedding_scores: dict[str, float],
    min_bm25: float,
    min_combined: float,
    rescue_embedding_min: float,
) -> list[Document]:
    """
    Gate documents for the LLM:

    - pass if ``combined_score`` meets hybrid floor, OR
    - BM25 alone meets the classic lexical floor, OR
    - dense similarity rescues a paraphrase (high raw-cosine ``embedding_score``).
    """
    kept: list[Document] = []
    for d in documents:
        did = str(d.id or "")
        if not did:
            continue
        comb = float(getattr(d, "score", 0.0) or 0.0)
        bm = float(bm25_scores.get(did, 0.0))
        emb = float(embedding_scores.get(did, 0.0))
        if comb >= min_combined or bm >= min_bm25 or emb >= rescue_embedding_min:
            kept.append(d)
    return kept
