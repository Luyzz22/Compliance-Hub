"""Tests for hybrid retrieval evaluation on a tiny synthetic corpus.

Validates that the evaluation pipeline computes correct metrics and that
BM25 retrieval returns meaningful results on known queries.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app.services.rag.bm25_retriever import BM25Index
from app.services.rag.confidence import compute_confidence
from app.services.rag.config import RAGConfig
from app.services.rag.corpus import Document, RetrievalResult
from app.services.rag.hybrid_retriever import HybridRetriever


def _load_rag_eval_script():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "rag_eval_hybrid.py"
    spec = importlib.util.spec_from_file_location("rag_eval_hybrid", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


TINY_CORPUS = [
    Document(
        doc_id="doc-a",
        title="Hochrisiko Definition",
        content=(
            "Ein KI-System gilt als Hochrisiko wenn es als Sicherheitskomponente "
            "eines Produkts dient das unter EU-Harmonisierungsrecht fällt"
        ),
        source="EU AI Act",
        section="Art. 6",
    ),
    Document(
        doc_id="doc-b",
        title="NIS2 Meldefrist",
        content=(
            "Wesentliche Einrichtungen müssen Sicherheitsvorfälle innerhalb von "
            "24 Stunden melden und einen Abschlussbericht innerhalb eines Monats"
        ),
        source="NIS2",
        section="Art. 23",
    ),
    Document(
        doc_id="doc-c",
        title="ISO 42001 Risikobewertung",
        content=(
            "Die Organisation muss einen Prozess zur KI-Risikobewertung definieren "
            "der Risiken identifiziert analysiert und Behandlungsmaßnahmen bestimmt"
        ),
        source="ISO 42001",
        section="A.6.2.6",
    ),
    Document(
        doc_id="doc-d",
        title="DSGVO Automatisierte Entscheidungen",
        content=(
            "Betroffene Personen haben das Recht nicht einer ausschließlich "
            "automatisierten Entscheidung unterworfen zu werden die rechtliche "
            "Wirkung entfaltet"
        ),
        source="DSGVO",
        section="Art. 22",
    ),
    Document(
        doc_id="doc-e",
        title="Verbotene KI Praktiken",
        content=(
            "Folgende KI Praktiken sind verboten Sozialkreditsysteme "
            "unterschwellige Manipulation Ausnutzung von Schwachstellen "
            "biometrische Echtzeit-Fernidentifizierung"
        ),
        source="EU AI Act",
        section="Art. 5",
    ),
]


class TestBM25Retriever:
    def test_basic_retrieval(self) -> None:
        index = BM25Index()
        index.build(TINY_CORPUS)
        results = index.query("Hochrisiko KI-System Sicherheitskomponente", k=3)
        assert len(results) > 0
        assert results[0].doc.doc_id == "doc-a"

    def test_nis2_query(self) -> None:
        index = BM25Index()
        index.build(TINY_CORPUS)
        results = index.query("Meldefrist Sicherheitsvorfälle NIS2", k=3)
        assert len(results) > 0
        assert results[0].doc.doc_id == "doc-b"

    def test_empty_query(self) -> None:
        index = BM25Index()
        index.build(TINY_CORPUS)
        results = index.query("", k=3)
        assert results == []

    def test_no_match_query(self) -> None:
        index = BM25Index()
        index.build(TINY_CORPUS)
        results = index.query("Fußball Bundesliga Ergebnis", k=3)
        assert len(results) == 0 or results[0].score < 0.5

    def test_scores_normalized(self) -> None:
        index = BM25Index()
        index.build(TINY_CORPUS)
        results = index.query("Risikobewertung ISO 42001", k=5)
        if results:
            assert results[0].bm25_score <= 1.0
            assert results[0].bm25_score >= 0.0

    def test_empty_corpus(self) -> None:
        index = BM25Index()
        index.build([])
        results = index.query("test", k=3)
        assert results == []


class TestHybridRetriever:
    def test_bm25_mode(self) -> None:
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(TINY_CORPUS, config)
        response = retriever.retrieve("Hochrisiko KI-System")
        assert response.retrieval_mode == "bm25"
        assert response.alpha_used == 0.0
        assert len(response.results) > 0

    def test_retrieval_response_fields(self) -> None:
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(TINY_CORPUS, config)
        response = retriever.retrieve("NIS2 Meldefrist")
        assert response.query_hash
        assert response.confidence_level in ("high", "medium", "low")
        assert 0.0 <= response.confidence_score <= 1.0

    def test_query_hash_deterministic(self) -> None:
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(TINY_CORPUS, config)
        r1 = retriever.retrieve("test query")
        r2 = retriever.retrieve("test query")
        assert r1.query_hash == r2.query_hash

    def test_different_queries_different_hashes(self) -> None:
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(TINY_CORPUS, config)
        r1 = retriever.retrieve("query A")
        r2 = retriever.retrieve("query B")
        assert r1.query_hash != r2.query_hash

    def test_hybrid_mode_falls_back_to_bm25_without_dense(self) -> None:
        """Hybrid mode falls back to BM25 when sentence-transformers isn't loaded."""
        config = RAGConfig(retrieval_mode="hybrid")
        retriever = HybridRetriever(TINY_CORPUS, config)
        response = retriever.retrieve("Hochrisiko")
        assert response.retrieval_mode in ("bm25", "hybrid")
        assert len(response.results) > 0


class TestConfidenceHeuristic:
    def test_high_confidence(self) -> None:
        results = [
            RetrievalResult(doc=TINY_CORPUS[0], score=0.85, bm25_score=0.80),
            RetrievalResult(doc=TINY_CORPUS[1], score=0.30, bm25_score=0.25),
        ]
        level, score = compute_confidence(results, RAGConfig())
        assert level == "high"
        assert score > 0.5

    def test_low_confidence(self) -> None:
        results = [
            RetrievalResult(doc=TINY_CORPUS[0], score=0.15, bm25_score=0.05),
        ]
        level, score = compute_confidence(results, RAGConfig())
        assert level == "low"
        assert score < 0.3

    def test_empty_results(self) -> None:
        level, score = compute_confidence([], RAGConfig())
        assert level == "low"
        assert score == 0.0

    def test_topk_gap_boost(self) -> None:
        """Large gap between rank-1 and rank-2 boosts medium → high."""
        config = RAGConfig(
            confidence_high_combined=0.70,
            confidence_high_bm25=0.30,
            confidence_medium_combined=0.35,
            confidence_medium_bm25=0.10,
            confidence_topk_gap_boost=0.10,
        )
        results = [
            RetrievalResult(doc=TINY_CORPUS[0], score=0.50, bm25_score=0.40),
            RetrievalResult(doc=TINY_CORPUS[1], score=0.20, bm25_score=0.15),
        ]
        level, _ = compute_confidence(results, config)
        assert level == "high"


class TestEvalMetrics:
    """Test the metric functions used by the evaluation script."""

    def test_recall_at_k(self) -> None:
        m = _load_rag_eval_script()
        assert m.recall_at_k(["a", "b", "c"], ["a", "b"], k=3) == 1.0
        assert m.recall_at_k(["a", "b", "c"], ["a", "d"], k=3) == 0.5
        assert m.recall_at_k(["a", "b", "c"], ["d", "e"], k=3) == 0.0

    def test_precision_at_k(self) -> None:
        m = _load_rag_eval_script()
        assert m.precision_at_k(["a", "b", "c"], ["a", "b"], k=3) == pytest.approx(2 / 3)
        assert m.precision_at_k(["a", "b", "c"], ["a"], k=3) == pytest.approx(1 / 3)

    def test_ndcg_at_k(self) -> None:
        m = _load_rag_eval_script()
        score = m.ndcg_at_k(["a", "b", "c"], ["a"], k=3)
        assert score == pytest.approx(1.0)

        score_bad = m.ndcg_at_k(["b", "c", "a"], ["a"], k=3)
        assert score_bad < 1.0

    def test_ndcg_no_relevant(self) -> None:
        m = _load_rag_eval_script()
        assert m.ndcg_at_k(["a", "b"], [], k=2) == 0.0

    def test_fusion_winner_prefers_hybrid(self) -> None:
        m = _load_rag_eval_script()
        summary = [
            {"mode": "bm25", "avg_recall_at_k": 0.1, "avg_precision_at_k": 0.1, "avg_ndcg_at_k": 0.1},
            {
                "mode": "hybrid",
                "alpha": 0.3,
                "setting": "hybrid_alpha0.3",
                "avg_recall_at_k": 0.5,
                "avg_precision_at_k": 0.5,
                "avg_ndcg_at_k": 0.5,
            },
        ]
        w = m._fusion_winner(summary)
        assert w["winner"] == "hybrid"
        assert w.get("best_alpha") == 0.3


def test_should_decline_weak_bm25_and_dense() -> None:
    from app.services.rag.confidence import should_decline_answer

    decline, reason = should_decline_answer(
        "medium",
        has_results=True,
        top_bm25=0.02,
        top_dense=0.05,
        bm25_floor=0.10,
        dense_threshold=0.25,
    )
    assert decline is True
    assert reason == "weak_bm25_and_dense"
