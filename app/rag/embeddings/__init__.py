"""Dense embedding helpers for hybrid RAG (query + document warm-up)."""

from __future__ import annotations

from app.rag.embeddings.runtime import (
    embed_query_for_hybrid,
    ensure_document_store_embeddings,
    reset_query_embedder_for_tests,
)

__all__ = [
    "embed_query_for_hybrid",
    "ensure_document_store_embeddings",
    "reset_query_embedder_for_tests",
]
