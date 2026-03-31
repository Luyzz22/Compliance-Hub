"""Hybrid retrieval combining BM25 and dense scoring with configurable fusion.

Score fusion formula:
    combined = (1 - alpha) * bm25_normalized + alpha * dense_score

The BM25 floor ensures documents below a minimum BM25 relevance are excluded
even if the dense retriever scores them highly—this prevents dense-only
hallucinations on queries outside the corpus domain.

Rescue tracking: When the top document in hybrid mode differs from the BM25-only
top document, the result is tagged as a "dense rescue" for audit/evidence logging.
"""

from __future__ import annotations

import hashlib
import logging

from app.services.rag.bm25_retriever import BM25Index
from app.services.rag.confidence import compute_confidence
from app.services.rag.config import RAGConfig
from app.services.rag.corpus import Document, RetrievalResponse, RetrievalResult
from app.services.rag.dense_retriever import DenseIndex

logger = logging.getLogger(__name__)


class HybridRetriever:
    def __init__(
        self,
        documents: list[Document],
        config: RAGConfig | None = None,
    ) -> None:
        self.config = config or RAGConfig()
        self.bm25_index = BM25Index()
        self.dense_index = DenseIndex()
        self.bm25_index.build(documents)
        if self.config.retrieval_mode == "hybrid":
            self.dense_index.build(documents, model_name=self.config.dense_model_name)

    def retrieve(
        self,
        query: str,
        k: int | None = None,
        alpha: float | None = None,
        mode: str | None = None,
    ) -> RetrievalResponse:
        k = k or self.config.retrieval_k
        alpha = alpha if alpha is not None else self.config.hybrid_alpha
        mode = mode or self.config.retrieval_mode

        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]

        if mode == "bm25" or not self.dense_index.is_available:
            results = self.bm25_index.query(query, k=k)
            effective_mode = "bm25"
            effective_alpha = 0.0
        else:
            results = self._hybrid_fuse(query, k=k, alpha=alpha)
            effective_mode = "hybrid"
            effective_alpha = alpha

        has_tenant_guidance = any(r.doc.is_tenant_guidance for r in results)
        confidence_level, confidence_score = compute_confidence(results, self.config)

        return RetrievalResponse(
            results=results,
            retrieval_mode=effective_mode,
            alpha_used=effective_alpha,
            query_hash=query_hash,
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            has_tenant_guidance=has_tenant_guidance,
        )

    def _hybrid_fuse(
        self,
        query: str,
        k: int,
        alpha: float,
    ) -> list[RetrievalResult]:
        fetch_k = k * 3
        bm25_results = self.bm25_index.query(query, k=fetch_k)
        dense_results = self.dense_index.query(query, k=fetch_k)

        bm25_by_id: dict[str, RetrievalResult] = {r.doc.doc_id: r for r in bm25_results}
        dense_by_id: dict[str, RetrievalResult] = {r.doc.doc_id: r for r in dense_results}

        all_doc_ids = set(bm25_by_id.keys()) | set(dense_by_id.keys())
        bm25_top_id = bm25_results[0].doc.doc_id if bm25_results else None

        fused: list[RetrievalResult] = []
        for doc_id in all_doc_ids:
            bm25_r = bm25_by_id.get(doc_id)
            dense_r = dense_by_id.get(doc_id)

            bm25_score = bm25_r.bm25_score if bm25_r else 0.0
            dense_score = dense_r.dense_score if dense_r else 0.0

            if bm25_score < self.config.bm25_floor:
                if dense_score < self.config.dense_score_threshold:
                    continue

            combined = (1 - alpha) * bm25_score + alpha * dense_score
            doc = (bm25_r or dense_r).doc  # type: ignore[union-attr]

            if bm25_score >= dense_score:
                rescue_source = "bm25"
            elif bm25_score > 0:
                rescue_source = "both"
            else:
                rescue_source = "dense"

            fused.append(
                RetrievalResult(
                    doc=doc,
                    score=combined,
                    bm25_score=bm25_score,
                    dense_score=dense_score,
                    rescue_source=rescue_source,
                )
            )

        fused.sort(key=lambda r: r.score, reverse=True)
        for rank, result in enumerate(fused[:k]):
            result.rank = rank + 1

        top_k = fused[:k]
        if top_k and bm25_top_id and top_k[0].doc.doc_id != bm25_top_id:
            logger.info(
                "Hybrid rescue: top doc changed from %s (BM25) to %s (hybrid)",
                bm25_top_id,
                top_k[0].doc.doc_id,
            )

        return top_k
