"""Tests for Wave 9 — Advisor preset micro-flows.

Covers:
- Preset input → query building (all 3 flows)
- Preset endpoint → generic advisor request mapping (channel, metadata, flow_type)
- Structured response shape with expected fields
- Evidence/metrics tagging with flow_type and channel
- Channel-specific formatting (DATEV structured, SAP structured, web default)
- flow_type in metrics aggregation
"""

from __future__ import annotations

from app.advisor.channels import AdvisorChannel, ChannelMetadata
from app.advisor.formatting import (
    derive_next_steps,
    derive_tags,
    format_answer_for_channel,
)
from app.advisor.metrics import aggregate_advisor_metrics
from app.advisor.presets import (
    EU_AI_ACT_RISK_EXTRA_TAGS,
    ISO42001_GAP_EXTRA_TAGS,
    NIS2_OBLIGATIONS_EXTRA_TAGS,
    PRESET_REGISTRY,
    EuAiActRiskAssessmentInput,
    FlowType,
    Iso42001GapCheckInput,
    Nis2ObligationsInput,
    build_eu_ai_act_risk_query,
    build_iso42001_gap_query,
    build_nis2_obligations_query,
)
from app.advisor.service import AdvisorRequest, run_advisor
from app.advisor.templates import (
    DISCLAIMER_KANZLEI,
    DISCLAIMER_KEINE_RECHTSBERATUNG,
)
from app.services.agents.advisor_compliance_agent import AdvisorComplianceAgent
from app.services.rag.config import RAGConfig
from app.services.rag.corpus import Document
from app.services.rag.evidence_store import (
    clear_for_tests as clear_evidence,
)
from app.services.rag.evidence_store import (
    list_advisor_agent_events,
)
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.llm import LlmCallContext, LlmResponse

MOCK_CORPUS = [
    Document(
        doc_id="p-1",
        title="EU AI Act Art. 6 Hochrisiko",
        content=(
            "Hochrisiko KI-Systeme sind solche die als Sicherheitskomponente "
            "unter EU-Harmonisierungsrecht fallen oder in Anhang III gelistet sind. "
            "Die Klassifizierung als Hochrisiko-System erfordert eine "
            "Konformitätsbewertung nach den Verfahren gemäß Art. 43."
        ),
        source="EU AI Act",
        section="Art. 6",
    ),
    Document(
        doc_id="p-2",
        title="NIS2 Art. 21 Risikomanagement",
        content=(
            "Wesentliche und wichtige Einrichtungen müssen technische, "
            "betriebliche und organisatorische Maßnahmen zum "
            "Risikomanagement ergreifen. KRITIS-nahe Zulieferer unterliegen "
            "besonderen Meldepflichten nach Art. 23."
        ),
        source="NIS2",
        section="Art. 21",
    ),
    Document(
        doc_id="p-3",
        title="ISO 42001 Anforderungen",
        content=(
            "ISO 42001 AI Management System erfordert ein KI-Governance-Framework "
            "mit Risikobewertung, Verantwortlichkeiten und kontinuierlicher "
            "Verbesserung. Gap-Analyse gegen die Norm identifiziert fehlende "
            "Prozesse und Kontrollen."
        ),
        source="ISO 42001",
        section="4-10",
    ),
]


def _mock_llm(prompt: str, context: LlmCallContext) -> LlmResponse:
    return LlmResponse(
        text=(
            "Basierend auf Art. 6 EU AI Act und Anhang III "
            "ist Ihr KI-System wahrscheinlich hochrisikorelevant."
        ),
        model_id="mock-model",
        input_tokens=50,
        output_tokens=30,
    )


def _make_agent(llm_fn=_mock_llm) -> AdvisorComplianceAgent:
    config = RAGConfig(retrieval_mode="bm25")
    retriever = HybridRetriever(MOCK_CORPUS, config)
    return AdvisorComplianceAgent(retriever=retriever, llm_fn=llm_fn)


# ---------------------------------------------------------------------------
# Query building
# ---------------------------------------------------------------------------


class TestQueryBuilding:
    def test_eu_ai_act_risk_query_contains_use_case(self) -> None:
        inp = EuAiActRiskAssessmentInput(
            use_case_description="Automatisierte Kreditwürdigkeitsprüfung",
            industry_sector="Finanzdienstleistungen",
            intended_purpose="Bonitätsbewertung natürlicher Personen",
        )
        q = build_eu_ai_act_risk_query(inp)
        assert "hochrisikorelevant" in q
        assert "Kreditwürdigkeitsprüfung" in q
        assert "Finanzdienstleistungen" in q
        assert "Art. 6" in q

    def test_eu_ai_act_risk_query_minimal(self) -> None:
        inp = EuAiActRiskAssessmentInput(
            use_case_description="Chatbot für FAQ",
        )
        q = build_eu_ai_act_risk_query(inp)
        assert "Chatbot" in q
        assert "Branche:" not in q

    def test_nis2_obligations_query_contains_role(self) -> None:
        inp = Nis2ObligationsInput(
            entity_role="KRITIS-naher Zulieferer",
            sector="Energie",
            employee_count="250+",
        )
        q = build_nis2_obligations_query(inp)
        assert "NIS2" in q
        assert "KRITIS-naher Zulieferer" in q
        assert "Energie" in q
        assert "250+" in q

    def test_nis2_obligations_query_minimal(self) -> None:
        inp = Nis2ObligationsInput(entity_role="Betreiber wesentlicher Dienste")
        q = build_nis2_obligations_query(inp)
        assert "Betreiber wesentlicher Dienste" in q
        assert "Sektor:" not in q

    def test_iso42001_gap_query_contains_measures(self) -> None:
        inp = Iso42001GapCheckInput(
            current_measures="Wir haben ein ISMS nach ISO 27001",
            ai_system_count="5",
        )
        q = build_iso42001_gap_query(inp)
        assert "ISO 42001" in q
        assert "ISMS" in q
        assert "5" in q

    def test_iso42001_gap_query_minimal(self) -> None:
        inp = Iso42001GapCheckInput(current_measures="Keine formalen KI-Governance-Maßnahmen")
        q = build_iso42001_gap_query(inp)
        assert "Lücken" in q
        assert "Keine formalen" in q


# ---------------------------------------------------------------------------
# Preset → generic AdvisorRequest mapping
# ---------------------------------------------------------------------------


class TestPresetRequestMapping:
    def setup_method(self) -> None:
        clear_evidence()

    def teardown_method(self) -> None:
        clear_evidence()

    def test_eu_ai_act_preset_maps_flow_type_and_tags(self) -> None:
        agent = _make_agent()
        request = AdvisorRequest(
            query=build_eu_ai_act_risk_query(
                EuAiActRiskAssessmentInput(
                    use_case_description="Automatisierte Gesichtserkennung",
                ),
            ),
            tenant_id="test-t",
            channel=AdvisorChannel.datev,
            channel_metadata=ChannelMetadata(datev_client_number="12345"),
            flow_type=FlowType.eu_ai_act_risk_assessment.value,
            extra_tags=EU_AI_ACT_RISK_EXTRA_TAGS,
        )

        resp = run_advisor(request, agent)

        assert resp.meta.flow_type == "eu_ai_act_risk_assessment"
        assert "eu_ai_act" in resp.tags
        assert "high_risk" in resp.tags
        assert resp.ref_ids.get("flow_type") == "eu_ai_act_risk_assessment"
        assert resp.ref_ids.get("datev_client_number") == "12345"

    def test_nis2_preset_maps_channel_and_flow_type(self) -> None:
        agent = _make_agent()
        request = AdvisorRequest(
            query=build_nis2_obligations_query(
                Nis2ObligationsInput(entity_role="KRITIS-naher Zulieferer"),
            ),
            tenant_id="test-t",
            channel=AdvisorChannel.sap,
            channel_metadata=ChannelMetadata(sap_document_id="SAP-001"),
            flow_type=FlowType.nis2_obligations.value,
            extra_tags=NIS2_OBLIGATIONS_EXTRA_TAGS,
        )

        resp = run_advisor(request, agent)

        assert resp.meta.flow_type == "nis2_obligations"
        assert resp.meta.channel == AdvisorChannel.sap
        assert "nis2" in resp.tags
        assert resp.ref_ids.get("sap_document_id") == "SAP-001"

    def test_iso42001_preset_web_channel_defaults(self) -> None:
        agent = _make_agent()
        request = AdvisorRequest(
            query=build_iso42001_gap_query(
                Iso42001GapCheckInput(
                    current_measures="Wir haben keine formalen KI-Governance-Prozesse",
                ),
            ),
            tenant_id="test-t",
            flow_type=FlowType.iso42001_gap_check.value,
            extra_tags=ISO42001_GAP_EXTRA_TAGS,
        )

        resp = run_advisor(request, agent)

        assert resp.meta.flow_type == "iso42001_gap_check"
        assert resp.meta.channel == AdvisorChannel.web
        assert "iso_42001" in resp.tags


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------


class TestPresetResponseShape:
    def setup_method(self) -> None:
        clear_evidence()

    def teardown_method(self) -> None:
        clear_evidence()

    def test_response_has_structured_fields(self) -> None:
        agent = _make_agent()
        request = AdvisorRequest(
            query=build_eu_ai_act_risk_query(
                EuAiActRiskAssessmentInput(
                    use_case_description="KI-gestützte Personalauswahl",
                ),
            ),
            tenant_id="test-t",
            flow_type=FlowType.eu_ai_act_risk_assessment.value,
            extra_tags=EU_AI_ACT_RISK_EXTRA_TAGS,
        )

        resp = run_advisor(request, agent)

        assert isinstance(resp.tags, list)
        assert isinstance(resp.suggested_next_steps, list)
        assert isinstance(resp.ref_ids, dict)
        assert resp.answer
        assert resp.meta.latency_ms is not None
        assert resp.meta.latency_ms > 0

    def test_datev_channel_uses_structured_format(self) -> None:
        agent = _make_agent()
        request = AdvisorRequest(
            query=build_eu_ai_act_risk_query(
                EuAiActRiskAssessmentInput(
                    use_case_description="Automatisierte Bilanzanalyse mit KI",
                ),
            ),
            tenant_id="test-t",
            channel=AdvisorChannel.datev,
            flow_type=FlowType.eu_ai_act_risk_assessment.value,
            extra_tags=EU_AI_ACT_RISK_EXTRA_TAGS,
        )

        resp = run_advisor(request, agent)

        assert "Schlagworte:" in resp.answer
        assert "Empfohlene nächste Schritte:" in resp.answer
        assert DISCLAIMER_KANZLEI in resp.answer

    def test_web_channel_uses_normal_format(self) -> None:
        agent = _make_agent()
        request = AdvisorRequest(
            query=build_eu_ai_act_risk_query(
                EuAiActRiskAssessmentInput(
                    use_case_description="Automatisierte Bilanzanalyse",
                ),
            ),
            tenant_id="test-t",
            channel=AdvisorChannel.web,
            flow_type=FlowType.eu_ai_act_risk_assessment.value,
            extra_tags=EU_AI_ACT_RISK_EXTRA_TAGS,
        )

        resp = run_advisor(request, agent)

        assert DISCLAIMER_KEINE_RECHTSBERATUNG in resp.answer
        assert "Schlagworte:" not in resp.answer


# ---------------------------------------------------------------------------
# Evidence & metrics flow_type tagging
# ---------------------------------------------------------------------------


class TestEvidenceAndMetrics:
    def setup_method(self) -> None:
        clear_evidence()

    def teardown_method(self) -> None:
        clear_evidence()

    def test_flow_type_logged_in_agent_events(self) -> None:
        agent = _make_agent()
        request = AdvisorRequest(
            query=build_eu_ai_act_risk_query(
                EuAiActRiskAssessmentInput(
                    use_case_description="KI für Qualitätskontrolle",
                ),
            ),
            tenant_id="preset-t",
            channel=AdvisorChannel.datev,
            flow_type=FlowType.eu_ai_act_risk_assessment.value,
            extra_tags=EU_AI_ACT_RISK_EXTRA_TAGS,
        )

        run_advisor(request, agent)

        events = list_advisor_agent_events("preset-t", limit=10)
        assert len(events) >= 1
        service_event = events[0]
        extra = service_event.get("extra", {})
        assert extra.get("flow_type") == "eu_ai_act_risk_assessment"
        assert extra.get("channel") == "datev"

    def test_flow_type_in_metrics_aggregation(self) -> None:
        agent = _make_agent()
        for ft, query_fn, inp in [
            (
                FlowType.eu_ai_act_risk_assessment,
                build_eu_ai_act_risk_query,
                EuAiActRiskAssessmentInput(
                    use_case_description="KI für Qualitätskontrolle in der Fertigung",
                ),
            ),
            (
                FlowType.nis2_obligations,
                build_nis2_obligations_query,
                Nis2ObligationsInput(entity_role="KRITIS-Betreiber"),
            ),
        ]:
            request = AdvisorRequest(
                query=query_fn(inp),
                tenant_id="metrics-t",
                flow_type=ft.value,
                extra_tags=PRESET_REGISTRY[ft]["extra_tags"],
            )
            run_advisor(request, agent)

        metrics = aggregate_advisor_metrics(tenant_id="metrics-t")
        ftd = metrics.flow_type_distribution
        assert ftd.get("eu_ai_act_risk_assessment", 0) >= 1
        assert ftd.get("nis2_obligations", 0) >= 1

    def test_sap_channel_in_metrics_distribution(self) -> None:
        agent = _make_agent()
        request = AdvisorRequest(
            query=build_nis2_obligations_query(
                Nis2ObligationsInput(entity_role="Digitaler Dienstleister"),
            ),
            tenant_id="sap-metrics-t",
            channel=AdvisorChannel.sap,
            flow_type=FlowType.nis2_obligations.value,
            extra_tags=NIS2_OBLIGATIONS_EXTRA_TAGS,
        )

        run_advisor(request, agent)

        metrics = aggregate_advisor_metrics(tenant_id="sap-metrics-t")
        assert metrics.channel_distribution.get("sap", 0) >= 1


# ---------------------------------------------------------------------------
# Channel-specific formatting
# ---------------------------------------------------------------------------


class TestChannelFormatting:
    def test_datev_structured_format_with_kanzlei_disclaimer(self) -> None:
        answer = "Dies ist eine Testantwort zum EU AI Act."
        tags = ["eu_ai_act", "high_risk"]
        steps = ["Konformitätsbewertung prüfen"]

        formatted = format_answer_for_channel(
            answer,
            AdvisorChannel.datev,
            tags=tags,
            next_steps=steps,
        )

        assert "Schlagworte: eu_ai_act, high_risk" in formatted
        assert "Konformitätsbewertung prüfen" in formatted
        assert DISCLAIMER_KANZLEI in formatted

    def test_sap_structured_format_with_short_disclaimer(self) -> None:
        answer = "NIS2-Pflichten für KRITIS-nahe Zulieferer."
        tags = ["nis2"]
        steps = ["Meldepflichten prüfen"]

        formatted = format_answer_for_channel(
            answer,
            AdvisorChannel.sap,
            tags=tags,
            next_steps=steps,
        )

        assert "Schlagworte: nis2" in formatted
        assert DISCLAIMER_KANZLEI not in formatted

    def test_web_channel_no_structured_fields_in_answer(self) -> None:
        answer = "Testantwort."
        formatted = format_answer_for_channel(
            answer,
            AdvisorChannel.web,
            tags=["eu_ai_act"],
            next_steps=["prüfen"],
        )
        assert "Schlagworte:" not in formatted

    def test_derive_tags_detects_preset_topics(self) -> None:
        tags = derive_tags(
            "Hochrisiko KI-System nach EU AI Act",
            "Art. 6 Konformitätsbewertung erforderlich",
        )
        assert "eu_ai_act" in tags
        assert "high_risk" in tags
        assert "article_reference" in tags

    def test_derive_next_steps_includes_ai_act_and_nis2(self) -> None:
        tags = ["eu_ai_act", "nis2", "high_risk"]
        steps = derive_next_steps(False, "high", tags)
        assert "EU AI Act Konformitätsbewertung prüfen" in steps
        assert "NIS2-Meldepflichten überprüfen" in steps
        assert "Hochrisiko-Klassifizierung dokumentieren" in steps


# ---------------------------------------------------------------------------
# Preset registry completeness
# ---------------------------------------------------------------------------


class TestPresetRegistry:
    def test_all_flow_types_in_registry(self) -> None:
        from app.advisor.presets import PRESET_REGISTRY

        for ft in FlowType:
            assert ft in PRESET_REGISTRY, f"{ft} missing from PRESET_REGISTRY"
            entry = PRESET_REGISTRY[ft]
            assert callable(entry["build_query"])
            assert isinstance(entry["extra_tags"], list)
            assert len(entry["extra_tags"]) > 0
