"""Runtime embedding of queries and (lazy) corpus documents for hybrid retrieval."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from haystack import Document

from app.rag.haystack_config import rag_embedding_model_id

if TYPE_CHECKING:
    from haystack.document_stores.in_memory import InMemoryDocumentStore

logger = logging.getLogger(__name__)

_query_embedder = None


def reset_query_embedder_for_tests() -> None:
    global _query_embedder
    _query_embedder = None


def embed_query_for_hybrid(query_de: str) -> list[float]:
    """
    Embed the advisor question (multilingual model from ``COMPLIANCEHUB_RAG_EMBEDDING_MODEL``).

    Tests should patch this function to avoid downloading weights.
    """
    global _query_embedder
    from haystack.components.embedders import SentenceTransformersTextEmbedder

    if _query_embedder is None:
        mid = rag_embedding_model_id()
        logger.info("rag_query_embedder_init model_id=%s", mid)
        _query_embedder = SentenceTransformersTextEmbedder(model=mid)
    vec = _query_embedder.run(text=query_de.strip())["embedding"]
    return [float(x) for x in vec]


def ensure_document_store_embeddings(document_store: InMemoryDocumentStore) -> None:
    """
    Embed any documents missing ``embedding`` (idempotent).

    Re-writes those rows in the in-memory store so ``InMemoryEmbeddingRetriever`` can run.
    """
    from haystack.components.embedders import SentenceTransformersDocumentEmbedder
    from haystack.document_stores.in_memory import InMemoryDocumentStore

    if not isinstance(document_store, InMemoryDocumentStore):
        raise TypeError("expected InMemoryDocumentStore")

    all_docs = document_store.filter_documents()
    need = [d for d in all_docs if d.embedding is None]
    if not need:
        return
    mid = rag_embedding_model_id()
    logger.info("rag_document_embedder_run count=%s model_id=%s", len(need), mid)
    emb = SentenceTransformersDocumentEmbedder(model=mid)
    out: list[Document] = list(emb.run(documents=need)["documents"])
    ids = [str(d.id) for d in need if d.id]
    if ids:
        document_store.delete_documents(document_ids=ids)
    document_store.write_documents(out)
