"""LangGraph advisor graph — same semantics as AdvisorComplianceAgent.run (mocked LLM)."""

from __future__ import annotations

import pytest

pytest.importorskip("langgraph")

from app.services.agents.advisor_langgraph import build_advisor_compliance_langgraph
from app.services.rag.config import RAGConfig
from app.services.rag.corpus import Document
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.llm import LlmCallContext, LlmResponse

from tests.test_advisor_agent import MOCK_CORPUS, _mock_llm


def test_langgraph_high_confidence_synthesizes() -> None:
    config = RAGConfig(retrieval_mode="bm25")
    retriever = HybridRetriever(MOCK_CORPUS, config)
    graph = build_advisor_compliance_langgraph(retriever, llm_fn=_mock_llm)
    out = graph.invoke(
        {
            "query": "Was sind Hochrisiko KI-Systeme nach EU AI Act?",
            "tenant_id": "t-graph",
            "trace_id": "trace-lg-1",
        }
    )
    st = out["_st"]
    assert not st.is_escalated
    assert "Mock-Antwort" in st.answer
    assert any(
        isinstance(t, dict) and t.get("trace_id") == "trace-lg-1" for t in st.agent_trace
    )


def test_langgraph_out_of_scope_escalates() -> None:
    config = RAGConfig(retrieval_mode="bm25")
    retriever = HybridRetriever(MOCK_CORPUS, config)
    graph = build_advisor_compliance_langgraph(retriever)
    out = graph.invoke({"query": "Wie wird das Wetter?", "tenant_id": "t2"})
    st = out["_st"]
    assert st.is_escalated


def test_langgraph_low_confidence_escalates() -> None:
    config = RAGConfig(retrieval_mode="bm25")
    empty_corpus = [
        Document(
            doc_id="irrelevant",
            title="Irrelevant",
            content="Kein Bezug zu NIS2 oder EU AI Act Thema",
            source="Other",
        ),
    ]
    retriever = HybridRetriever(empty_corpus, config)
    graph = build_advisor_compliance_langgraph(retriever)
    out = graph.invoke(
        {
            "query": "Spezifische NIS2 Anforderungen für Energieversorger",
            "tenant_id": "t3",
        }
    )
    assert out["_st"].is_escalated
