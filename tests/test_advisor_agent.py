"""Tests for the AdvisorComplianceAgent LangGraph-style agent.

Validates graph paths:
- High-confidence RAG → synthesize_answer
- Low-confidence → escalate_to_human
- Out-of-scope intent → escalate_to_human
- Tenant guidance policy → escalate when guidance missing

All LLM and RAG outputs are mocked for determinism.
"""

from __future__ import annotations

from app.services.agents.advisor_compliance_agent import (
    AdvisorComplianceAgent,
    AdvisorState,
    IntentType,
    check_confidence,
    classify_intent,
    escalate_to_human,
)
from app.services.rag.config import RAGConfig
from app.services.rag.corpus import Document, RetrievalResponse
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.llm import LlmCallContext, LlmResponse

MOCK_CORPUS = [
    Document(
        doc_id="mock-1",
        title="EU AI Act Art. 6",
        content=(
            "Hochrisiko KI-Systeme sind solche die als Sicherheitskomponente "
            "unter EU-Harmonisierungsrecht fallen oder in Anhang III gelistet sind"
        ),
        source="EU AI Act",
        section="Art. 6",
    ),
    Document(
        doc_id="mock-2",
        title="NIS2 Art. 23",
        content=(
            "Meldepflicht für Sicherheitsvorfälle 24 Stunden Frühwarnung "
            "72 Stunden Vorfallmeldung ein Monat Abschlussbericht"
        ),
        source="NIS2",
        section="Art. 23",
    ),
    Document(
        doc_id="mock-guidance",
        title="Tenant Guidance: Hochrisiko-Bewertung",
        content="Mandantenspezifische Anleitung zur Hochrisiko-Bewertung",
        source="Tenant Guidance",
        section="",
        is_tenant_guidance=True,
    ),
]


def _mock_llm(prompt: str, context: LlmCallContext) -> LlmResponse:
    return LlmResponse(
        text="Mock-Antwort: Basierend auf [mock-1] sind Hochrisiko-Systeme definiert als...",
        model_id="mock-model",
        input_tokens=100,
        output_tokens=50,
    )


class TestIntentClassification:
    def test_informational_intent(self) -> None:
        state = AdvisorState(query="Was sind Hochrisiko-KI-Systeme?")
        state = classify_intent(state)
        assert state.intent == IntentType.informational

    def test_action_intent(self) -> None:
        state = AdvisorState(query="Erstelle einen Compliance-Bericht für das System")
        state = classify_intent(state)
        assert state.intent == IntentType.action_oriented

    def test_out_of_scope_intent(self) -> None:
        state = AdvisorState(query="Wie wird das Wetter morgen in München?")
        state = classify_intent(state)
        assert state.intent == IntentType.out_of_scope

    def test_trace_recorded(self) -> None:
        state = AdvisorState(query="Test query")
        state = classify_intent(state)
        assert len(state.agent_trace) == 1
        assert state.agent_trace[0]["node"] == "classify_intent"


class TestConfidencePolicy:
    def test_high_confidence_routes_to_synthesize(self) -> None:
        state = AdvisorState(confidence_level="high")
        state.retrieval_response = RetrievalResponse(
            results=[], retrieval_mode="bm25", alpha_used=0.0,
            query_hash="abc", confidence_level="high", has_tenant_guidance=False,
        )
        result = check_confidence(state)
        assert result == "synthesize"

    def test_low_confidence_routes_to_escalate(self) -> None:
        state = AdvisorState(confidence_level="low")
        result = check_confidence(state)
        assert result == "escalate"
        assert "Geringe Konfidenz" in state.escalation_reason

    def test_missing_tenant_guidance_escalates(self) -> None:
        state = AdvisorState(confidence_level="medium")
        state.retrieval_response = RetrievalResponse(
            results=[], retrieval_mode="hybrid", alpha_used=0.3,
            query_hash="def", confidence_level="medium", has_tenant_guidance=False,
        )
        result = check_confidence(state, tenant_has_guidance=True)
        assert result == "escalate"
        assert "Mandantenspezifische" in state.escalation_reason


class TestEscalation:
    def test_escalation_sets_flags(self) -> None:
        state = AdvisorState(
            escalation_reason="Test reason",
            tenant_id="test-tenant",
        )
        state = escalate_to_human(state)
        assert state.is_escalated is True
        assert "Menschliche Prüfung" in state.answer
        assert "Test reason" in state.answer

    def test_escalation_trace(self) -> None:
        state = AdvisorState(escalation_reason="Low confidence")
        state = escalate_to_human(state)
        assert any(t["node"] == "escalate_to_human" for t in state.agent_trace)


class TestAdvisorComplianceAgentIntegration:
    def test_high_confidence_path(self) -> None:
        """Informational query with good BM25 match → synthesize_answer."""
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(MOCK_CORPUS, config)
        agent = AdvisorComplianceAgent(
            retriever=retriever,
            llm_fn=_mock_llm,
        )

        state = agent.run(
            query="Was sind Hochrisiko KI-Systeme nach EU AI Act?",
            tenant_id="test-tenant",
        )

        assert not state.is_escalated
        assert "Mock-Antwort" in state.answer
        nodes = [t["node"] for t in state.agent_trace]
        assert "classify_intent" in nodes
        assert "run_rag_query" in nodes
        assert "synthesize_answer" in nodes

    def test_out_of_scope_escalation(self) -> None:
        """Out-of-scope query → immediate escalation, no RAG."""
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(MOCK_CORPUS, config)
        agent = AdvisorComplianceAgent(retriever=retriever)

        state = agent.run(query="Wie wird das Wetter?", tenant_id="test-tenant")

        assert state.is_escalated
        assert state.intent == IntentType.out_of_scope
        nodes = [t["node"] for t in state.agent_trace]
        assert "run_rag_query" not in nodes
        assert "escalate_to_human" in nodes

    def test_low_confidence_escalation(self) -> None:
        """Query with no relevant corpus docs → low confidence → escalation."""
        config = RAGConfig(retrieval_mode="bm25")
        empty_corpus = [
            Document(
                doc_id="irrelevant",
                title="Irrelevant",
                content="Dieses Dokument hat keinen Bezug zur Anfrage",
                source="Other",
            ),
        ]
        retriever = HybridRetriever(empty_corpus, config)
        agent = AdvisorComplianceAgent(retriever=retriever)

        state = agent.run(
            query="Spezifische NIS2 Anforderungen für Energieversorger",
            tenant_id="test-tenant",
        )

        assert state.is_escalated
        nodes = [t["node"] for t in state.agent_trace]
        assert "escalate_to_human" in nodes

    def test_tenant_guidance_policy(self) -> None:
        """Tenant has guidance but retrieval misses it → escalation."""
        non_guidance_corpus = [
            Document(
                doc_id="law-only",
                title="EU AI Act Art. 6 Hochrisiko Klassifizierung",
                content=(
                    "Hochrisiko KI-Systeme Klassifizierung Bewertung System "
                    "Sicherheitskomponente EU-Harmonisierungsrecht Konformität "
                    "Anhang III Anwendungsbereiche Hochrisiko-Klassifizierung"
                ),
                source="EU AI Act",
                is_tenant_guidance=False,
            ),
        ]
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(non_guidance_corpus, config)
        agent = AdvisorComplianceAgent(
            retriever=retriever,
            llm_fn=_mock_llm,
            tenant_has_guidance=True,
        )

        state = agent.run(
            query="Hochrisiko Klassifizierung Bewertung System",
            tenant_id="tenant-with-guidance",
        )

        assert state.is_escalated
        assert "Mandantenspezifische" in state.escalation_reason

    def test_llm_failure_returns_safe_fallback(self) -> None:
        """LLM failure → safe fallback response, not a crash."""
        def _failing_llm(prompt: str, context: LlmCallContext) -> LlmResponse:
            raise RuntimeError("LLM unavailable")

        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(MOCK_CORPUS, config)
        agent = AdvisorComplianceAgent(
            retriever=retriever,
            llm_fn=_failing_llm,
        )

        state = agent.run(
            query="Was sind Hochrisiko KI-Systeme?",
            tenant_id="test-tenant",
        )

        assert "Compliance-Berater" in state.answer
        assert not state.is_escalated

    def test_agent_trace_completeness(self) -> None:
        """Verify that the agent trace captures all node executions."""
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(MOCK_CORPUS, config)
        agent = AdvisorComplianceAgent(
            retriever=retriever,
            llm_fn=_mock_llm,
        )

        state = agent.run(
            query="ISO 42001 Risikobewertung",
            tenant_id="test-tenant",
        )

        assert len(state.agent_trace) >= 2
        for entry in state.agent_trace:
            assert "node" in entry
