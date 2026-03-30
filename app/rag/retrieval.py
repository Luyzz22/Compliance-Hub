"""Merged BM25 retrieval: global regulatory corpus + optional tenant guidance overlays."""

from __future__ import annotations

import logging
from dataclasses import replace

from haystack import Document
from haystack.components.retrievers import InMemoryBM25Retriever
from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.rag.haystack_config import rag_global_top_k, rag_merged_top_k, rag_tenant_overlay_top_k

logger = logging.getLogger(__name__)

_GLOBAL_SCOPE = "global"
_TENANT_SCOPE = "tenant_guidance"


def _filter_global() -> dict:
    return {"field": "rag_scope", "operator": "==", "value": _GLOBAL_SCOPE}


def _filter_tenant(tenant_id: str) -> dict:
    return {
        "operator": "AND",
        "conditions": [
            {"field": "tenant_id", "operator": "==", "value": tenant_id},
            {"field": "rag_scope", "operator": "==", "value": _TENANT_SCOPE},
        ],
    }


def merged_bm25_retrieve(
    document_store: InMemoryDocumentStore,
    *,
    query: str,
    tenant_id: str,
) -> list[Document]:
    """
    Retrieve global law snippets always; add tenant-specific guidance when present.

    Documents are returned with ``score`` set (Haystack BM25). Deduplicated by ``id``,
    highest score kept, then truncated to merged top-k.
    """
    q = query.strip()
    kg = rag_global_top_k()
    kt = rag_tenant_overlay_top_k()
    cap = rag_merged_top_k()

    gr = InMemoryBM25Retriever(document_store=document_store, top_k=kg)
    g_out = gr.run(query=q, filters=_filter_global())
    g_docs = list(g_out.get("documents") or [])

    tr = InMemoryBM25Retriever(document_store=document_store, top_k=kt)
    t_out = tr.run(query=q, filters=_filter_tenant(tenant_id.strip()))
    t_docs = list(t_out.get("documents") or [])

    by_id: dict[str, Document] = {}
    for d in g_docs + t_docs:
        did = str(d.id or "")
        if not did:
            continue
        score = float(getattr(d, "score", 0.0) or 0.0)
        prev = by_id.get(did)
        if prev is None or float(getattr(prev, "score", 0.0) or 0.0) < score:
            by_id[did] = replace(d, score=score)

    merged = sorted(
        by_id.values(),
        key=lambda x: float(getattr(x, "score", 0.0) or 0.0),
        reverse=True,
    )
    merged = merged[:cap]
    logger.debug(
        "rag_merged_retrieval tenant=%s global_hits=%s tenant_hits=%s merged=%s",
        tenant_id,
        len(g_docs),
        len(t_docs),
        len(merged),
    )
    return merged


def documents_scores_and_ids(documents: list[Document]) -> tuple[list[float], list[str]]:
    scores = [float(getattr(d, "score", 0.0) or 0.0) for d in documents]
    ids = [str(d.id or "") for d in documents]
    return scores, ids


def filter_documents_by_min_score(documents: list[Document], min_score: float) -> list[Document]:
    return [d for d in documents if float(getattr(d, "score", 0.0) or 0.0) >= min_score]


def is_tenant_guidance_document(doc: Document) -> bool:
    meta = doc.meta or {}
    return str(meta.get("rag_scope", "")).strip() == _TENANT_SCOPE
