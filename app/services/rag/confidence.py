"""Confidence heuristic for RAG retrieval results.

Derives confidence from combined_score and top-k score gaps while enforcing
a BM25 floor to prevent dense-only hallucinations.

Confidence levels (for downstream agent/UI decisions):
- "high":   Strong BM25 + combined signal → safe for auto-answer.
- "medium": Moderate signal → answer with caveats, flag for review.
- "low":    Weak signal → escalate to human, do not auto-answer.

The logic is deterministic and documented for EU AI Act Art. 13 transparency
requirements and ISO 42001 A.6.2.6 (AI system performance monitoring).
"""

from __future__ import annotations

from app.services.rag.config import RAGConfig
from app.services.rag.corpus import RetrievalResult


def compute_confidence(
    results: list[RetrievalResult],
    config: RAGConfig,
) -> tuple[str, float]:
    """Return (confidence_level, confidence_score) for the retrieval results.

    confidence_score is a float 0.0–1.0 summarizing retrieval quality.
    confidence_level is one of "high", "medium", "low".
    """
    if not results:
        return "low", 0.0

    top = results[0]
    combined = top.score
    bm25 = top.bm25_score

    topk_gap = 0.0
    if len(results) >= 2:
        topk_gap = results[0].score - results[1].score

    base_level = _base_level(combined, bm25, config)

    if base_level == "medium" and topk_gap >= config.confidence_topk_gap_boost:
        base_level = "high"

    score = _compute_score(combined, bm25, topk_gap, config)

    return base_level, round(score, 3)


def _base_level(combined: float, bm25: float, config: RAGConfig) -> str:
    if combined >= config.confidence_high_combined and bm25 >= config.confidence_high_bm25:
        return "high"
    if combined >= config.confidence_medium_combined and bm25 >= config.confidence_medium_bm25:
        return "medium"
    return "low"


def _compute_score(combined: float, bm25: float, topk_gap: float, config: RAGConfig) -> float:
    """Weighted blend of signals into a single 0–1 score."""
    bm25_weight = 0.4
    combined_weight = 0.4
    gap_weight = 0.2
    gap_norm = min(topk_gap / 0.3, 1.0) if topk_gap > 0 else 0.0

    raw = bm25_weight * bm25 + combined_weight * combined + gap_weight * gap_norm
    return min(max(raw, 0.0), 1.0)


def should_decline_answer(
    confidence_level: str,
    *,
    tenant_expects_guidance: bool = False,
    has_tenant_guidance: bool = False,
    has_results: bool = True,
    top_bm25: float | None = None,
    top_dense: float | None = None,
    bm25_floor: float | None = None,
    dense_threshold: float | None = None,
) -> tuple[bool, str | None]:
    """Conservative gate for retrieval-only API (no auto-answer when unsafe).

    Documented decline reasons for audits / AI Act evidence:
    - ``no_hits``: no retrieval results.
    - ``low_confidence``: confidence heuristic is ``low``.
    - ``tenant_guidance_missing``: tenant expects mandanten guidance but top results lack it.
    - ``weak_bm25_and_dense``: top hit is weak on *both* lexical (BM25) and dense channels.
    """
    if not has_results:
        return True, "no_hits"
    if confidence_level == "low":
        return True, "low_confidence"
    if tenant_expects_guidance and not has_tenant_guidance:
        return True, "tenant_guidance_missing"
    if (
        top_bm25 is not None
        and top_dense is not None
        and has_results
    ):
        bf = bm25_floor if bm25_floor is not None else 0.10
        dt = dense_threshold if dense_threshold is not None else 0.25
        if top_bm25 < bf * 0.5 and top_dense < dt * 0.5:
            return True, "weak_bm25_and_dense"
    return False, None
