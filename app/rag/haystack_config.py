"""
Haystack / RAG configuration (pilot: in-memory BM25; optional hybrid BM25 + dense).

Environment:
- COMPLIANCEHUB_ADVISOR_RAG_RETRIEVAL_MODE: ``bm25`` (default) or ``hybrid`` (BM25 + dense merge).
- COMPLIANCEHUB_RAG_RETRIEVER: legacy alias; ``embedding`` maps to ``hybrid`` for backward compatibility.
- COMPLIANCEHUB_RAG_EMBEDDING_MODEL: Hugging Face id for dense retriever (e.g. multilingual MPNet).
- COMPLIANCEHUB_RAG_HYBRID_* : convex combination (1-alpha)*norm_bm25 + alpha*norm_dense, score audit fields.
"""

from __future__ import annotations

import os


def rag_advisor_retrieval_mode() -> str:
    """
    Advisor EU regulatory RAG retrieval graph: ``bm25`` | ``hybrid``.

    Default ``bm25`` until hybrid is validated in production.
    """
    raw = os.getenv("COMPLIANCEHUB_ADVISOR_RAG_RETRIEVAL_MODE", "").strip().lower()
    if raw in ("bm25", "hybrid"):
        return raw
    legacy = os.getenv("COMPLIANCEHUB_RAG_RETRIEVER", "bm25").strip().lower()
    if legacy == "embedding":
        return "hybrid"
    return "bm25"


def rag_retriever_backend() -> str:
    """Legacy name; prefer ``rag_advisor_retrieval_mode``."""
    m = rag_advisor_retrieval_mode()
    return "embedding" if m == "hybrid" else "bm25"


def rag_hybrid_dense_alpha() -> float:
    """Weight on dense branch in convex combine: (1-alpha)*bm25_norm + alpha*dense_norm."""
    raw = os.getenv("COMPLIANCEHUB_RAG_HYBRID_DENSE_ALPHA", "0.5").strip()
    try:
        a = float(raw)
    except ValueError:
        return 0.5
    return min(1.0, max(0.0, a))


def rag_hybrid_candidate_pool_k() -> int:
    """BM25 + dense candidates merged before re-ranking to merged top-k."""
    raw = os.getenv("COMPLIANCEHUB_RAG_HYBRID_POOL_K", "24").strip()
    try:
        k = int(raw)
    except ValueError:
        return 24
    return max(rag_merged_top_k(), min(k, 50))


def rag_hybrid_min_combined_score() -> float:
    """Minimum combined score (0..1) for a document to enter the LLM context in hybrid mode."""
    raw = os.getenv("COMPLIANCEHUB_RAG_HYBRID_MIN_COMBINED_SCORE", "0.22").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.22


def rag_hybrid_rescue_embedding_min() -> float:
    """
    If BM25 is below ``rag_bm25_min_score`` but raw cosine dense similarity meets this floor,
    the document may still pass (embedding rescues borderline lexical queries).
    """
    raw = os.getenv("COMPLIANCEHUB_RAG_HYBRID_RESCUE_EMBEDDING_MIN", "0.62").strip()
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.62


def rag_hybrid_confidence_high_min() -> float:
    """High-confidence floor on combined normalized scores (hybrid path)."""
    raw = os.getenv("COMPLIANCEHUB_RAG_HYBRID_CONFIDENCE_HIGH_MIN", "0.55").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.55


def rag_hybrid_confidence_gap_min() -> float:
    """Top-1 vs top-2 combined gap for ``high`` in hybrid mode."""
    raw = os.getenv("COMPLIANCEHUB_RAG_HYBRID_CONFIDENCE_GAP_MIN", "0.07").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.07


def rag_embedding_model_id() -> str:
    return os.getenv(
        "COMPLIANCEHUB_RAG_EMBEDDING_MODEL",
        "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    ).strip()


def rag_merged_top_k() -> int:
    """Max documents passed to the prompt after merging global + tenant hits (cap 10)."""
    raw = os.getenv(
        "COMPLIANCEHUB_RAG_MERGED_TOP_K",
        os.getenv("COMPLIANCEHUB_RAG_TOP_K", "5"),
    ).strip()
    try:
        k = int(raw)
    except ValueError:
        return 5
    return max(1, min(k, 10))


def rag_global_top_k() -> int:
    raw = os.getenv("COMPLIANCEHUB_RAG_GLOBAL_TOP_K", "5").strip()
    try:
        k = int(raw)
    except ValueError:
        return 5
    return max(1, min(k, 10))


def rag_tenant_overlay_top_k() -> int:
    raw = os.getenv("COMPLIANCEHUB_RAG_TENANT_TOP_K", "3").strip()
    try:
        k = int(raw)
    except ValueError:
        return 3
    return max(1, min(k, 10))


def rag_bm25_min_score() -> float:
    """Drop hits below this BM25 score before LLM (Haystack-normalized scores)."""
    raw = os.getenv("COMPLIANCEHUB_RAG_BM25_MIN_SCORE", "0.08").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.08


def rag_confidence_high_score_min() -> float:
    raw = os.getenv("COMPLIANCEHUB_RAG_CONFIDENCE_HIGH_MIN_SCORE", "0.28").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.28


def rag_confidence_gap_min() -> float:
    raw = os.getenv("COMPLIANCEHUB_RAG_CONFIDENCE_GAP_MIN", "0.06").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.06


def rag_retriever_top_k() -> int:
    """Backward-compatible alias for merged cap."""
    return rag_merged_top_k()
