"""
Haystack / RAG configuration (pilot: in-memory BM25; embeddings + pgvector later).

Environment:
- COMPLIANCEHUB_RAG_RETRIEVER: ``bm25`` (default) or ``embedding`` (requires model download).
- COMPLIANCEHUB_RAG_EMBEDDING_MODEL: Hugging Face id for dense retriever (e.g. multilingual MPNet).
- COMPLIANCEHUB_RAG_PGVECTOR_* : reserved for future Postgres + pgvector document store.
"""

from __future__ import annotations

import os


def rag_retriever_backend() -> str:
    return os.getenv("COMPLIANCEHUB_RAG_RETRIEVER", "bm25").strip().lower()


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
