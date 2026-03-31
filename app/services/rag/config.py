"""RAG pipeline configuration.

All tunable parameters are explicit and documented for auditability
under EU AI Act Art. 13 (transparency) and ISO 42001 A.6.2.6.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RAGConfig:
    """Immutable configuration for the RAG retrieval pipeline.

    Attributes documented for audit trail / AI Act evidence.
    """

    retrieval_k: int = 5
    """Number of documents to retrieve per query."""

    hybrid_alpha: float = float(os.getenv("COMPLIANCEHUB_HYBRID_ALPHA", "0.30"))
    """Weight of dense score in hybrid fusion: combined = (1-α)·BM25_norm + α·dense.

    Chosen via offline evaluation (see scripts/rag_eval_hybrid.py).
    α=0.0 → pure BM25, α=1.0 → pure dense.  Default 0.30 reflects
    conservative bias toward exact-match BM25 to reduce hallucination risk.
    """

    bm25_floor: float = float(os.getenv("COMPLIANCEHUB_BM25_FLOOR", "0.10"))
    """Minimum BM25 normalized score for a document to be considered.

    Documents below this floor are excluded even if the dense score is high,
    preventing dense-only hallucinations on out-of-corpus queries.
    """

    dense_score_threshold: float = float(
        os.getenv("COMPLIANCEHUB_DENSE_THRESHOLD", "0.25")
    )
    """Minimum dense cosine-similarity for a document to be a "rescue" candidate.

    Only documents above this threshold are eligible to be promoted by
    the dense retriever when BM25 ranks them lower.
    """

    confidence_high_combined: float = 0.65
    confidence_high_bm25: float = 0.25
    confidence_medium_combined: float = 0.35
    confidence_medium_bm25: float = 0.10
    confidence_topk_gap_boost: float = 0.15
    """If the gap between rank-1 and rank-2 combined scores exceeds this
    value, confidence is boosted one level (medium→high)."""

    retrieval_mode: str = os.getenv("COMPLIANCEHUB_RETRIEVAL_MODE", "hybrid")
    """'bm25' or 'hybrid'.  Controls which pipeline path is used at runtime."""

    dense_model_name: str = os.getenv(
        "COMPLIANCEHUB_DENSE_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    """Sentence-transformer model for dense embeddings (multilingual for DE/EN)."""

    alpha_grid: list[float] = field(
        default_factory=lambda: [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    )
    """Alpha values to sweep during offline evaluation."""


DEFAULT_CONFIG = RAGConfig()
