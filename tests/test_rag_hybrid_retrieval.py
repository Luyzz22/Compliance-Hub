"""Wave 6: hybrid BM25 + dense retrieval (deterministic, no model download in CI)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.rag.embeddings.runtime import reset_query_embedder_for_tests
from app.rag.models import EuRegRagLlmCitation, EuRegRagLlmOutput
from app.rag.pipelines.eu_ai_act_nis2_pipeline import run_eu_ai_act_nis2_pipeline
from app.rag.retrievers.hybrid_eu_ai_act import hybrid_merged_retrieve


@pytest.fixture(autouse=True)
def _reset_embedder():
    reset_query_embedder_for_tests()
    yield
    reset_query_embedder_for_tests()


def _store_semantic_rescue() -> InMemoryDocumentStore:
    """BM25 favours lexical-noise doc; shared embedding direction favours semantic-target."""
    store = InMemoryDocumentStore()
    qdim = [1.0, 0.0, 0.0]
    store.write_documents(
        [
            Document(
                id="lexical-noise-chunk",
                content=(
                    "Was ist bei einer erheblichen IT-Störung bei wesentlichen "
                    "Einrichtungen zu melden "
                    "NIS2 Behörden Vorfall unverzüglich Stichwortliste"
                ),
                meta={"source": "noise", "section": "Lexikal", "rag_scope": "global"},
                embedding=[0.0, 1.0, 0.0],
            ),
            Document(
                id="semantic-target-chunk",
                content=(
                    "Sicherheitsvorfälle mit erheblicher Auswirkung sind den zuständigen "
                    "Behörden mitzuteilen (inhaltliche Paraphrase ohne Query-Wortlaut)."
                ),
                meta={"source": "norm", "section": "Meldung", "rag_scope": "global"},
                embedding=qdim,
            ),
        ],
    )
    return store


def test_hybrid_merged_retrieve_ranks_by_combined_score() -> None:
    store = _store_semantic_rescue()
    pack = hybrid_merged_retrieve(
        store,
        query="Was ist bei einer erheblichen IT-Störung bei wesentlichen Einrichtungen zu melden?",
        tenant_id="t-hyb-1",
        query_embedding=[1.0, 0.0, 0.0],
        alpha=0.75,
        pool_k=10,
    )
    assert pack.documents[0].id == "semantic-target-chunk"
    assert pack.hit_audit[0]["doc_id"] == "semantic-target-chunk"
    assert pack.hit_audit[0]["combined_score"] > pack.hit_audit[1]["combined_score"]


def test_hybrid_pipeline_rescues_semantic_hit_and_medium_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ADVISOR_RAG_RETRIEVAL_MODE", "hybrid")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_BM25_MIN_SCORE", "0.35")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_HYBRID_MIN_COMBINED_SCORE", "0.15")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_HYBRID_RESCUE_EMBEDDING_MIN", "0.55")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_HYBRID_CONFIDENCE_HIGH_MIN", "0.45")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_HYBRID_CONFIDENCE_GAP_MIN", "0.02")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_HYBRID_DENSE_ALPHA", "0.75")

    store = _store_semantic_rescue()
    fixed = EuRegRagLlmOutput(
        answer_de="Die Meldepflicht richtet sich nach den Vorgaben für wesentliche Einrichtungen.",
        citations=[
            EuRegRagLlmCitation(
                doc_id="semantic-target-chunk",
                source="norm",
                section="Meldung",
            ),
        ],
    )

    with (
        patch(
            "app.rag.pipelines.eu_ai_act_nis2_pipeline.ensure_document_store_embeddings",
            lambda _s: None,
        ),
        patch(
            "app.rag.pipelines.eu_ai_act_nis2_pipeline.embed_query_for_hybrid",
            return_value=[1.0, 0.0, 0.0],
        ),
        patch(
            "app.rag.pipelines.eu_ai_act_nis2_pipeline.generate_eu_reg_rag_llm_output",
            return_value=fixed,
        ),
    ):
        pr = run_eu_ai_act_nis2_pipeline(
            question_de=(
                "Was ist bei einer erheblichen IT-Störung bei wesentlichen Einrichtungen zu melden?"
            ),
            tenant_id="t-hyb-pipe",
            user_role="advisor",
            document_store=store,
            session=None,
        )

    assert pr.retrieval_mode == "hybrid"
    assert pr.retrieval_hit_audit
    assert pr.documents_for_prompt
    assert pr.documents_for_prompt[0].id == "semantic-target-chunk"
    assert pr.confidence_level in ("medium", "high")


def test_bm25_only_misses_semantic_doc_without_lexical_overlap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Single paraphrase doc: BM25 stays below min score; no LLM (contrast with hybrid rescue)."""
    monkeypatch.setenv("COMPLIANCEHUB_ADVISOR_RAG_RETRIEVAL_MODE", "bm25")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_BM25_MIN_SCORE", "0.25")
    store = InMemoryDocumentStore()
    store.write_documents(
        [
            Document(
                id="semantic-target-chunk",
                content=(
                    "Sicherheitsvorfälle mit erheblicher Auswirkung sind den zuständigen "
                    "Behörden mitzuteilen (inhaltliche Paraphrase ohne Query-Wortlaut)."
                ),
                meta={"source": "norm", "section": "Meldung", "rag_scope": "global"},
                embedding=[1.0, 0.0, 0.0],
            ),
        ],
    )
    with patch(
        "app.rag.pipelines.eu_ai_act_nis2_pipeline.generate_eu_reg_rag_llm_output",
    ) as mock_llm:
        pr = run_eu_ai_act_nis2_pipeline(
            question_de=(
                "Was ist bei einer erheblichen IT-Störung bei wesentlichen Einrichtungen zu melden?"
            ),
            tenant_id="t-bm25",
            user_role="advisor",
            document_store=store,
            session=None,
        )
    mock_llm.assert_not_called()
    assert pr.used_llm is False
    assert pr.confidence_level == "low"


def test_ingest_corpus_embeds_with_mock_transformer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.ingest_eu_ai_act_nis2_corpus import main

    calls: list[int] = []

    class _FakeEmb:
        def run(self, documents: list) -> dict:
            calls.append(len(documents))
            out = []
            for d in documents:
                out.append(Document(id=d.id, content=d.content, meta=d.meta, embedding=[0.1, 0.2]))
            return {"documents": out}

    monkeypatch.setenv("COMPLIANCEHUB_RAG_EMBEDDING_MODEL", "mock-model")
    monkeypatch.setattr(
        "scripts.ingest_eu_ai_act_nis2_corpus.SentenceTransformersDocumentEmbedder",
        lambda **_: _FakeEmb(),
    )
    monkeypatch.setattr(
        "scripts.ingest_eu_ai_act_nis2_corpus.load_default_corpus_documents",
        lambda: [
            Document(
                id="ingest-test-0",
                content="Test chunk für Embedding.",
                meta={"source": "t.md", "rag_scope": "global"},
            ),
        ],
    )
    monkeypatch.setattr("sys.argv", ["ingest_eu_ai_act_nis2_corpus.py", "--with-embeddings"])
    assert main() == 0
    assert calls == [1]
