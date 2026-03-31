"""Shared in-memory document store for the EU regulatory RAG pilot (thread-safe init)."""

from __future__ import annotations

import threading

from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.rag.ingestion import load_default_corpus_documents

_lock = threading.Lock()
_store: InMemoryDocumentStore | None = None


def get_eu_reg_document_store() -> InMemoryDocumentStore:
    """Singleton store seeded with the shipped pilot corpus."""
    global _store
    with _lock:
        if _store is None:
            _store = InMemoryDocumentStore()
            docs = load_default_corpus_documents()
            if docs:
                _store.write_documents(docs)
        return _store


def reset_eu_reg_document_store_for_tests() -> None:
    """Test hook: clear singleton so the next get_* rebuilds from corpus."""
    global _store
    with _lock:
        _store = None


def replace_eu_reg_document_store_for_tests(store: InMemoryDocumentStore) -> None:
    """Test hook: inject a pre-seeded store."""
    global _store
    with _lock:
        _store = store


def register_tenant_guidance_documents(tenant_id: str, documents: list) -> None:
    """
    Append mandanten-spezifische Leitfaden-Fragmente (metadata: rag_scope=tenant_guidance).

    ``documents`` are Haystack ``Document`` instances; ``meta`` wird ergänzt, nicht überschrieben.
    """
    from haystack import Document

    store = get_eu_reg_document_store()
    to_write: list[Document] = []
    for d in documents:
        meta = dict(d.meta or {})
        meta["tenant_id"] = tenant_id.strip()
        meta["rag_scope"] = "tenant_guidance"
        to_write.append(Document(id=d.id, content=d.content, meta=meta))
    if to_write:
        store.write_documents(to_write)
