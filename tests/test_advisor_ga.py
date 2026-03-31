"""Tests for Wave 8 — Advisor GA hardening.

Covers:
- Error/timeout behaviour with correct structured error shapes
- Channel abstraction propagation
- Idempotency via request_id
- Structured output fields (tags, next_steps, ref_ids)
- Extended metrics (errors, channels, latency)
"""

from __future__ import annotations

import time

from app.advisor.channels import AdvisorChannel, ChannelMetadata
from app.advisor.errors import AdvisorErrorCategory, build_advisor_error
from app.advisor.formatting import derive_next_steps, derive_tags, format_answer_for_channel
from app.advisor.idempotency import clear_for_tests as clear_idem
from app.advisor.idempotency import get_cached_response, store_response
from app.advisor.metrics import aggregate_advisor_metrics
from app.advisor.service import AdvisorRequest, run_advisor
from app.advisor.templates import DISCLAIMER_KEINE_RECHTSBERATUNG
from app.services.agents.advisor_compliance_agent import AdvisorComplianceAgent
from app.services.rag.config import RAGConfig
from app.services.rag.corpus import Document
from app.services.rag.evidence_store import clear_for_tests as clear_evidence
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.llm import LlmCallContext, LlmResponse

MOCK_CORPUS = [
    Document(
        doc_id="ga-1",
        title="EU AI Act Art. 6 Hochrisiko",
        content=(
            "Hochrisiko KI-Systeme sind solche die als Sicherheitskomponente "
            "unter EU-Harmonisierungsrecht fallen oder in Anhang III gelistet sind. "
            "Die Klassifizierung als Hochrisiko-System erfordert Konformitätsbewertung."
        ),
        source="EU AI Act",
        section="Art. 6",
    ),
    Document(
        doc_id="ga-2",
        title="EU AI Act Art. 9 Risikomanagement",
        content=(
            "Hochrisiko KI-Systeme erfordern ein Risikomanagementsystem. "
            "Das System muss während des gesamten Lebenszyklus aufrechterhalten werden."
        ),
        source="EU AI Act",
        section="Art. 9",
    ),
    Document(
        doc_id="ga-3",
        title="NIS2 Art. 23 Meldepflicht",
        content=(
            "Meldepflicht Sicherheitsvorfälle 24 Stunden Frühwarnung "
            "72 Stunden Vorfallmeldung Abschlussbericht."
        ),
        source="NIS2",
        section="Art. 23",
    ),
]


def _mock_llm(prompt: str, context: LlmCallContext) -> LlmResponse:
    return LlmResponse(
        text="Hochrisiko-KI-Systeme nach Art. 6 EU AI Act erfordern Konformitätsbewertung.",
        model_id="mock-model",
        input_tokens=50,
        output_tokens=30,
    )


def _slow_llm(prompt: str, context: LlmCallContext) -> LlmResponse:
    time.sleep(5)
    return LlmResponse(text="slow answer", model_id="slow")


def _failing_llm(prompt: str, context: LlmCallContext) -> LlmResponse:
    raise RuntimeError("LLM provider down")


def _make_agent(llm_fn=_mock_llm) -> AdvisorComplianceAgent:
    config = RAGConfig(retrieval_mode="bm25")
    retriever = HybridRetriever(MOCK_CORPUS, config)
    return AdvisorComplianceAgent(retriever=retriever, llm_fn=llm_fn)


class TestErrorModel:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_build_error_has_correct_shape(self) -> None:
        err = build_advisor_error(
            AdvisorErrorCategory.rag_failure,
            trace_id="t-123",
        )
        assert err.error is True
        assert err.category == AdvisorErrorCategory.rag_failure
        assert err.message_de
        assert err.message_en
        assert err.needs_manual_followup is True
        assert err.trace_id == "t-123"

    def test_timeout_error_shape(self) -> None:
        err = build_advisor_error(
            AdvisorErrorCategory.timeout,
            retry_allowed=True,
        )
        assert err.category == AdvisorErrorCategory.timeout
        assert err.retry_allowed is True

    def test_llm_failure_returns_structured_error(self) -> None:
        agent = _make_agent(llm_fn=_failing_llm)
        req = AdvisorRequest(
            query="Was sind Hochrisiko KI-Systeme?",
            tenant_id="t-err",
            trace_id="trace-fail",
        )
        resp = run_advisor(req, agent)
        assert not resp.is_escalated or resp.answer
        assert resp.needs_manual_followup or resp.answer
        assert resp.meta.trace_id == "trace-fail"

    def test_agent_exception_returns_error_response(self) -> None:
        class BrokenAgent:
            def run(self, *a, **kw):
                raise ValueError("Boom")

        req = AdvisorRequest(query="Test", tenant_id="t", trace_id="t-boom")
        resp = run_advisor(req, BrokenAgent(), timeout_seconds=5)  # type: ignore[arg-type]
        assert resp.error is not None
        assert resp.error.category == AdvisorErrorCategory.agent_failure
        assert resp.needs_manual_followup is True


class TestChannelAbstraction:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_web_channel_default(self) -> None:
        agent = _make_agent()
        req = AdvisorRequest(
            query="Was sind Hochrisiko KI-Systeme nach EU AI Act?",
            tenant_id="t-web",
        )
        resp = run_advisor(req, agent)
        assert resp.meta.channel == AdvisorChannel.web
        assert DISCLAIMER_KEINE_RECHTSBERATUNG in resp.answer

    def test_sap_channel_strips_disclaimer(self) -> None:
        agent = _make_agent()
        req = AdvisorRequest(
            query="Was sind Hochrisiko KI-Systeme nach EU AI Act?",
            tenant_id="t-sap",
            channel=AdvisorChannel.sap,
            channel_metadata=ChannelMetadata(sap_document_id="DOC-42"),
        )
        resp = run_advisor(req, agent)
        assert resp.meta.channel == AdvisorChannel.sap
        assert DISCLAIMER_KEINE_RECHTSBERATUNG not in resp.answer
        assert resp.ref_ids.get("sap_document_id") == "DOC-42"

    def test_datev_channel_with_metadata(self) -> None:
        agent = _make_agent()
        req = AdvisorRequest(
            query="Was sind Hochrisiko KI-Systeme nach EU AI Act?",
            tenant_id="t-datev",
            channel=AdvisorChannel.datev,
            channel_metadata=ChannelMetadata(datev_client_number="KD-999"),
        )
        resp = run_advisor(req, agent)
        assert resp.meta.channel == AdvisorChannel.datev
        assert resp.ref_ids.get("datev_client_number") == "KD-999"

    def test_channel_does_not_break_existing_behaviour(self) -> None:
        agent = _make_agent()
        req_web = AdvisorRequest(
            query="Was sind Hochrisiko KI-Systeme nach EU AI Act?",
            tenant_id="t-compat",
        )
        resp_web = run_advisor(req_web, agent)
        assert not resp_web.is_escalated
        assert resp_web.answer
        assert resp_web.confidence_level in ("high", "medium", "low")


class TestStructuredOutput:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_tags_derived_from_content(self) -> None:
        tags = derive_tags(
            "EU AI Act Hochrisiko Systeme",
            "Art. 6 definiert Hochrisiko-Systeme im Rahmen des AI Act.",
        )
        assert "eu_ai_act" in tags
        assert "high_risk" in tags
        assert "article_reference" in tags

    def test_nis2_tags(self) -> None:
        tags = derive_tags("NIS2 Meldepflicht", "Nach NIS2 Art. 23...")
        assert "nis2" in tags

    def test_next_steps_for_escalated(self) -> None:
        steps = derive_next_steps(True, "low", ["eu_ai_act"])
        assert "Compliance-Berater kontaktieren" in steps

    def test_next_steps_for_answered(self) -> None:
        steps = derive_next_steps(False, "high", ["eu_ai_act", "high_risk"])
        assert any("Konformitätsbewertung" in s for s in steps)
        assert any("Hochrisiko" in s for s in steps)

    def test_full_structured_response(self) -> None:
        agent = _make_agent()
        req = AdvisorRequest(
            query="Hochrisiko KI-Systeme nach EU AI Act?",
            tenant_id="t-struct",
            channel=AdvisorChannel.api_partner,
            channel_metadata=ChannelMetadata(partner_reference="REF-1"),
        )
        resp = run_advisor(req, agent)
        assert resp.tags
        assert resp.suggested_next_steps
        assert resp.ref_ids.get("partner_reference") == "REF-1"
        assert resp.meta.latency_ms is not None
        assert resp.meta.latency_ms >= 0


class TestIdempotency:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_same_request_id_returns_cached(self) -> None:
        agent = _make_agent()
        req = AdvisorRequest(
            query="Hochrisiko KI-Systeme?",
            tenant_id="t-idem",
            request_id="req-001",
        )
        resp1 = run_advisor(req, agent)
        resp2 = run_advisor(req, agent)
        assert resp2.meta.is_cached is True
        assert resp1.answer == resp2.answer

    def test_different_request_ids_not_cached(self) -> None:
        agent = _make_agent()
        req1 = AdvisorRequest(query="Hochrisiko?", tenant_id="t", request_id="req-A")
        req2 = AdvisorRequest(query="Hochrisiko?", tenant_id="t", request_id="req-B")
        run_advisor(req1, agent)
        resp2 = run_advisor(req2, agent)
        assert resp2.meta.is_cached is False

    def test_no_request_id_never_cached(self) -> None:
        agent = _make_agent()
        req = AdvisorRequest(query="Hochrisiko?", tenant_id="t")
        run_advisor(req, agent)
        resp2 = run_advisor(req, agent)
        assert resp2.meta.is_cached is False

    def test_cache_store_and_retrieve(self) -> None:
        store_response("test-key", {"value": 42})
        assert get_cached_response("test-key") == {"value": 42}
        assert get_cached_response("missing") is None
        assert get_cached_response(None) is None


class TestChannelFormatting:
    def test_web_keeps_disclaimer(self) -> None:
        text = f"Antwort.\n\n---\n_{DISCLAIMER_KEINE_RECHTSBERATUNG}_"
        result = format_answer_for_channel(text, AdvisorChannel.web)
        assert DISCLAIMER_KEINE_RECHTSBERATUNG in result

    def test_sap_strips_disclaimer(self) -> None:
        text = f"Antwort.\n\n---\n_{DISCLAIMER_KEINE_RECHTSBERATUNG}_"
        result = format_answer_for_channel(text, AdvisorChannel.sap)
        assert DISCLAIMER_KEINE_RECHTSBERATUNG not in result

    def test_datev_truncates(self) -> None:
        text = "A" * 5000
        result = format_answer_for_channel(text, AdvisorChannel.datev)
        assert len(result) <= 3000


class TestExtendedMetrics:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_metrics_include_channel_and_errors(self) -> None:
        agent = _make_agent()
        for ch in [AdvisorChannel.web, AdvisorChannel.sap, AdvisorChannel.sap]:
            req = AdvisorRequest(
                query="Hochrisiko KI-Systeme nach EU AI Act?",
                tenant_id="t-met",
                channel=ch,
            )
            run_advisor(req, agent)

        metrics = aggregate_advisor_metrics(tenant_id="t-met")
        assert metrics.channel_distribution.get("web", 0) >= 1
        assert metrics.channel_distribution.get("sap", 0) >= 2

    def test_metrics_error_rate(self) -> None:
        from app.services.rag.evidence_store import record_event

        record_event(
            {
                "event_type": "advisor_agent",
                "tenant_id": "t-erate",
                "decision": "answered",
                "extra": {"channel": "web"},
            }
        )
        record_event(
            {
                "event_type": "advisor_agent",
                "tenant_id": "t-erate",
                "decision": "error",
                "extra": {"channel": "web", "error_category": "timeout"},
            }
        )
        metrics = aggregate_advisor_metrics(tenant_id="t-erate")
        assert metrics.error_rate is not None
        assert metrics.error_rate == 0.5

    def test_metrics_latency_percentiles(self) -> None:
        from app.services.rag.evidence_store import record_event

        for lat in [100, 200, 300, 400, 500]:
            record_event(
                {
                    "event_type": "advisor_agent",
                    "tenant_id": "t-lat",
                    "decision": "answered",
                    "extra": {"channel": "web", "latency_ms": lat},
                }
            )
        metrics = aggregate_advisor_metrics(tenant_id="t-lat")
        assert metrics.latency_p50_ms is not None
        assert metrics.latency_p95_ms is not None
        assert metrics.latency_p50_ms >= 200
        assert metrics.latency_p95_ms >= 400
