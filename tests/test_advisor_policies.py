"""Tests for Wave 7 agent policy refinements.

Validates:
- Sensitive topic detection (keywords + patterns)
- Prohibited topic → refusal template
- Sensitive + low/medium confidence → escalation
- Out-of-scope → refusal template
- Normal answer includes disclaimer
"""

from __future__ import annotations

from app.advisor.sensitive_topics import check_sensitive_topic
from app.advisor.templates import (
    DISCLAIMER_KEINE_RECHTSBERATUNG,
    REFUSAL_OUT_OF_SCOPE,
    REFUSAL_PROHIBITED_TOPIC,
)
from app.services.agents.advisor_compliance_agent import (
    AdvisorComplianceAgent,
    AdvisorState,
    check_confidence,
    check_sensitive_topics,
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
]


def _mock_llm(prompt: str, context: LlmCallContext) -> LlmResponse:
    return LlmResponse(
        text="Mock-Antwort basierend auf Quellen.",
        model_id="mock-model",
        input_tokens=50,
        output_tokens=30,
    )


class TestSensitiveTopicDetection:
    def test_normal_query_not_sensitive(self) -> None:
        result = check_sensitive_topic("Was sind Hochrisiko-KI-Systeme?")
        assert not result.is_sensitive
        assert not result.is_prohibited

    def test_biometric_keyword(self) -> None:
        result = check_sensitive_topic("Wie ist biometrische Kategorisierung geregelt?")
        assert result.is_sensitive
        assert not result.is_prohibited
        assert result.matched_rule_id in ("sensitive_keyword", "sensitive_pattern")

    def test_emotion_recognition(self) -> None:
        result = check_sensitive_topic("Darf man Emotionserkennung am Arbeitsplatz einsetzen?")
        assert result.is_sensitive
        assert result.matched_term in ("emotionserkennung", "Emotionserkennung")

    def test_workforce_surveillance(self) -> None:
        result = check_sensitive_topic("Regeln zur Arbeitnehmerüberwachung mit KI")
        assert result.is_sensitive

    def test_social_scoring_prohibited(self) -> None:
        result = check_sensitive_topic("Ist social scoring in der EU erlaubt?")
        assert result.is_sensitive
        assert result.is_prohibited
        assert result.matched_rule_id == "prohibited_topic"

    def test_predictive_policing_prohibited(self) -> None:
        result = check_sensitive_topic("predictive policing Systeme bewerten")
        assert result.is_prohibited

    def test_deepfake_sensitive(self) -> None:
        result = check_sensitive_topic("Wie reguliert der AI Act Deepfake-Technologien?")
        assert result.is_sensitive
        assert not result.is_prohibited


class TestSensitiveTopicAgentNode:
    def test_check_sensitive_topics_node_safe(self) -> None:
        state = AdvisorState(query="EU AI Act Anforderungen")
        state = check_sensitive_topics(state)
        assert state.sensitive_topic is not None
        assert not state.sensitive_topic.is_sensitive
        assert any(t["node"] == "check_sensitive_topics" for t in state.agent_trace)

    def test_check_sensitive_topics_node_detected(self) -> None:
        state = AdvisorState(query="Gesichtserkennung am Arbeitsplatz")
        state = check_sensitive_topics(state)
        assert state.sensitive_topic is not None
        assert state.sensitive_topic.is_sensitive
        trace = next(t for t in state.agent_trace if t["node"] == "check_sensitive_topics")
        assert trace["is_sensitive"] is True


class TestPolicyEscalation:
    def test_sensitive_low_confidence_escalates(self) -> None:
        state = AdvisorState(confidence_level="low")
        state = check_sensitive_topics(AdvisorState(query="Emotionserkennung regulierung"))
        state.confidence_level = "low"
        state.retrieval_response = RetrievalResponse(
            results=[],
            retrieval_mode="bm25",
            alpha_used=0.0,
            query_hash="x",
            confidence_level="low",
            has_tenant_guidance=False,
        )
        result = check_confidence(state)
        assert result == "escalate"
        assert "Sensibles Thema" in state.escalation_reason

    def test_sensitive_medium_confidence_escalates(self) -> None:
        state = check_sensitive_topics(AdvisorState(query="biometrische Kategorisierung Pflichten"))
        state.confidence_level = "medium"
        state.retrieval_response = RetrievalResponse(
            results=[],
            retrieval_mode="bm25",
            alpha_used=0.0,
            query_hash="y",
            confidence_level="medium",
            has_tenant_guidance=False,
        )
        result = check_confidence(state)
        assert result == "escalate"

    def test_sensitive_high_confidence_synthesizes(self) -> None:
        state = check_sensitive_topics(AdvisorState(query="Gesichtserkennung Regeln"))
        state.confidence_level = "high"
        state.retrieval_response = RetrievalResponse(
            results=[],
            retrieval_mode="bm25",
            alpha_used=0.0,
            query_hash="z",
            confidence_level="high",
            has_tenant_guidance=False,
        )
        result = check_confidence(state)
        assert result == "synthesize"


class TestProhibitedTopicRefusal:
    def test_prohibited_topic_immediate_refusal(self) -> None:
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(MOCK_CORPUS, config)
        agent = AdvisorComplianceAgent(retriever=retriever, llm_fn=_mock_llm)

        state = agent.run(
            query="Wie implementiert man social scoring?",
            tenant_id="test-tenant",
        )

        assert state.is_escalated
        assert REFUSAL_PROHIBITED_TOPIC == state.answer
        nodes = [t["node"] for t in state.agent_trace]
        assert "check_sensitive_topics" in nodes
        assert "run_rag_query" not in nodes

    def test_prohibited_logs_policy_rule(self) -> None:
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(MOCK_CORPUS, config)
        agent = AdvisorComplianceAgent(retriever=retriever)

        state = agent.run(
            query="social scoring System bauen",
            tenant_id="test-tenant",
        )

        esc_trace = next(t for t in state.agent_trace if t["node"] == "escalate_to_human")
        assert esc_trace["policy_rule_id"] == "prohibited_topic"


class TestOutOfScopeRefusal:
    def test_out_of_scope_uses_template(self) -> None:
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(MOCK_CORPUS, config)
        agent = AdvisorComplianceAgent(retriever=retriever)

        state = agent.run(query="Wie wird das Wetter?", tenant_id="t")
        assert state.is_escalated
        assert state.answer == REFUSAL_OUT_OF_SCOPE


RICH_CORPUS = [
    Document(
        doc_id="rich-1",
        title="EU AI Act Art. 6 Hochrisiko",
        content=(
            "Hochrisiko KI-Systeme sind solche die als Sicherheitskomponente "
            "unter EU-Harmonisierungsrecht fallen oder in Anhang III gelistet sind. "
            "Die Klassifizierung als Hochrisiko-System erfordert ein umfassendes "
            "Konformitätsbewertungsverfahren."
        ),
        source="EU AI Act",
        section="Art. 6",
    ),
    Document(
        doc_id="rich-2",
        title="EU AI Act Art. 9 Risikomanagement",
        content=(
            "Hochrisiko KI-Systeme erfordern ein Risikomanagementsystem. "
            "Das System muss während des gesamten Lebenszyklus des "
            "KI-Systems aufrechterhalten werden."
        ),
        source="EU AI Act",
        section="Art. 9",
    ),
    Document(
        doc_id="rich-3",
        title="EU AI Act Art. 10 Daten-Governance",
        content=(
            "Hochrisiko KI-Systeme müssen mit Datensätzen trainiert werden die "
            "bestimmte Qualitätskriterien erfüllen. Daten-Governance umfasst "
            "Erhebung Annotation und Vorverarbeitung."
        ),
        source="EU AI Act",
        section="Art. 10",
    ),
]


class TestNormalAnswerDisclaimer:
    def test_normal_answer_includes_disclaimer(self) -> None:
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(RICH_CORPUS, config)
        agent = AdvisorComplianceAgent(retriever=retriever, llm_fn=_mock_llm)

        state = agent.run(
            query="Was sind Hochrisiko KI-Systeme nach EU AI Act?",
            tenant_id="t",
        )

        assert not state.is_escalated
        assert DISCLAIMER_KEINE_RECHTSBERATUNG in state.answer

    def test_answered_event_logged(self) -> None:
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(RICH_CORPUS, config)
        agent = AdvisorComplianceAgent(retriever=retriever, llm_fn=_mock_llm)

        state = agent.run(
            query="Was sind Hochrisiko KI-Systeme nach EU AI Act?",
            tenant_id="t",
        )

        nodes = [t["node"] for t in state.agent_trace]
        assert "synthesize_answer" in nodes
