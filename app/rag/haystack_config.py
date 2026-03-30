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


def rag_retriever_top_k() -> int:
    raw = os.getenv("COMPLIANCEHUB_RAG_TOP_K", "5").strip()
    try:
        k = int(raw)
    except ValueError:
        return 5
    return max(1, min(k, 20))
