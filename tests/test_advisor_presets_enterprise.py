"""Tests for Wave 9.1 — Enterprise advisor presets.

Covers:
- EnterpriseContext (tenant_id, client_id, system_id) propagation
- GRC field derivation for each preset type
- Preset service layer (anti-corruption boundary)
- PresetResult contract shape (human/machine/grc separation)
- Idempotency at preset-service level
- Evidence/metrics tagging with client_id, system_id, flow_type
- Backward compatibility (legacy tenant_id still works)
"""

from __future__ import annotations

from app.advisor.channels import AdvisorChannel, ChannelMetadata
from app.advisor.enterprise_context import EnterpriseContext
from app.advisor.idempotency import clear_for_tests as clear_idem
from app.advisor.metrics import aggregate_advisor_metrics
from app.advisor.preset_models import (
    RESPONSE_CONTRACT_VERSION,
    AiActRiskPresetInput,
    Iso42001GapCheckPresetInput,
    Nis2ObligationsPresetInput,
    PresetResult,
)
from app.advisor.preset_service import (
    run_eu_ai_act_risk_preset,
    run_iso42001_gap_preset,
    run_nis2_obligations_preset,
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
        doc_id="e-1",
        title="EU AI Act Art. 6 Hochrisiko",
        content=(
            "Hochrisiko KI-Systeme nach Art. 6 und Anhang III "
            "erfordern eine Konformitätsbewertung. Systeme zur "
            "Kreditwürdigkeitsprüfung fallen unter Anhang III Nr. 5."
        ),
        source="EU AI Act",
        section="Art. 6",
    ),
    Document(
        doc_id="e-2",
        title="NIS2 Art. 21 Risikomanagement",
        content=(
            "Wesentliche Einrichtungen müssen Risikomanagement, "
            "Meldepflichten (24 Stunden Frühwarnung, 72 Stunden "
            "Vorfallmeldung) und Governance-Maßnahmen umsetzen. "
            "KRITIS-nahe Zulieferer in der Lieferkette unterliegen "
            "besonderen Pflichten."
        ),
        source="NIS2",
        section="Art. 21",
    ),
    Document(
        doc_id="e-3",
        title="ISO 42001 Governance",
        content=(
            "ISO 42001 erfordert Governance, Risikobewertung, "
            "Datenmanagement, Monitoring und Transparenz. "
            "Organisationen mit ISO 27001 haben erhebliche "
            "Überschneidungen, müssen aber KI-spezifische "
            "Kontrollen ergänzen."
        ),
        source="ISO 42001",
        section="4-10",
    ),
]


def _mock_llm(prompt: str, context: LlmCallContext) -> LlmResponse:
    return LlmResponse(
        text=(
            "Basierend auf Art. 6 und Anhang III ist dieses "
            "Hochrisiko-KI-System konformitätsbewertungspflichtig."
        ),
        model_id="mock-model",
        input_tokens=50,
        output_tokens=30,
    )


def _make_agent() -> AdvisorComplianceAgent:
    config = RAGConfig(retrieval_mode="bm25")
    retriever = HybridRetriever(MOCK_CORPUS, config)
    return AdvisorComplianceAgent(retriever=retriever, llm_fn=_mock_llm)


# ---------------------------------------------------------------------------
# Enterprise context propagation
# ---------------------------------------------------------------------------


class TestEnterpriseContextPropagation:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_client_id_propagated_to_evidence(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(
                tenant_id="kanzlei-t",
                client_id="mandant-42",
            ),
            use_case_description=("KI-gestützte Kreditwürdigkeitsprüfung für Privatkunden"),
            channel=AdvisorChannel.datev,
        )

        result = run_eu_ai_act_risk_preset(inp, agent=agent)

        assert result.meta.context.client_id == "mandant-42"
        assert result.meta.context.tenant_id == "kanzlei-t"
        assert result.machine.ref_ids.get("client_id") == "mandant-42"

        events = list_advisor_agent_events("kanzlei-t", limit=10)
        assert len(events) >= 1
        svc = events[0]
        assert svc.get("extra", {}).get("client_id") == "mandant-42"

    def test_system_id_propagated_to_evidence(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(
                tenant_id="acme-gmbh",
                system_id="HR-AI-01",
            ),
            use_case_description="Automatisierte Personalauswahl",
        )

        result = run_eu_ai_act_risk_preset(inp, agent=agent)

        assert result.meta.context.system_id == "HR-AI-01"
        assert result.machine.ref_ids.get("system_id") == "HR-AI-01"

        events = list_advisor_agent_events("acme-gmbh", limit=10)
        svc = events[0]
        assert svc.get("extra", {}).get("system_id") == "HR-AI-01"

    def test_legacy_tenant_id_still_works(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            tenant_id="legacy-t",
            use_case_description="Legacy-Format Kreditprüfung",
        )

        result = run_eu_ai_act_risk_preset(inp, agent=agent)
        assert result.meta.context.tenant_id == "legacy-t"

    def test_client_id_in_metrics_aggregation(self) -> None:
        agent = _make_agent()
        for cid in ["mandant-1", "mandant-2", "mandant-1"]:
            inp = AiActRiskPresetInput(
                context=EnterpriseContext(
                    tenant_id="metrics-t",
                    client_id=cid,
                ),
                use_case_description="Testfall für Mandantenmetrik",
            )
            run_eu_ai_act_risk_preset(inp, agent=agent)

        metrics = aggregate_advisor_metrics(tenant_id="metrics-t")
        cid_dist = metrics.client_id_distribution
        assert cid_dist.get("mandant-1", 0) >= 2
        assert cid_dist.get("mandant-2", 0) >= 1


# ---------------------------------------------------------------------------
# GRC field derivation
# ---------------------------------------------------------------------------


class TestGrcDerivation:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_ai_act_risk_grc_fields(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(tenant_id="grc-t"),
            use_case_description="KI-Kreditwürdigkeitsprüfung",
            industry_sector="Finanzdienstleistungen",
        )

        result = run_eu_ai_act_risk_preset(inp, agent=agent)

        grc = result.grc
        assert grc.get("risk_category") in (
            "high_risk",
            "limited_risk",
            "minimal_risk",
            "unclassified",
        )
        assert grc.get("high_risk_likelihood") in (
            "likely",
            "unlikely",
            "unclear",
            "unknown",
        )
        assert isinstance(grc.get("conformity_assessment_required"), (bool, type(None)))

    def test_nis2_grc_fields(self) -> None:
        agent = _make_agent()
        inp = Nis2ObligationsPresetInput(
            context=EnterpriseContext(tenant_id="grc-t"),
            entity_role="KRITIS-naher Zulieferer",
            sector="Energie",
        )

        result = run_nis2_obligations_preset(inp, agent=agent)

        grc = result.grc
        assert isinstance(grc.get("obligation_tags"), list)
        assert isinstance(grc.get("reporting_deadlines"), list)
        assert grc.get("nis2_entity_type") in (
            "essential",
            "important",
            "",
            "out_of_scope",
        )

    def test_iso42001_grc_fields(self) -> None:
        agent = _make_agent()
        inp = Iso42001GapCheckPresetInput(
            context=EnterpriseContext(tenant_id="grc-t"),
            current_measures=("ISO 27001 zertifiziert, kein formales KI-Governance-Framework"),
        )

        result = run_iso42001_gap_preset(inp, agent=agent)

        grc = result.grc
        assert isinstance(grc.get("control_families"), list)
        assert grc.get("gap_severity") in (
            "critical",
            "major",
            "minor",
            "none",
            "unknown",
        )
        assert grc.get("iso27001_overlap") is True


# ---------------------------------------------------------------------------
# PresetResult contract shape
# ---------------------------------------------------------------------------


class TestPresetResultContract:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_result_has_human_machine_grc_meta(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(tenant_id="shape-t"),
            use_case_description="Testfall Vertragsstruktur",
        )

        result = run_eu_ai_act_risk_preset(inp, agent=agent)

        assert isinstance(result, PresetResult)
        assert result.human.answer_de
        assert isinstance(result.machine.tags, list)
        assert isinstance(result.machine.suggested_next_steps, list)
        assert isinstance(result.grc, dict)
        assert result.meta.version == RESPONSE_CONTRACT_VERSION
        assert result.meta.flow_type == "eu_ai_act_risk_assessment"
        assert result.meta.latency_ms is not None

    def test_version_is_v1(self) -> None:
        assert RESPONSE_CONTRACT_VERSION == "v1"

    def test_ref_ids_contain_flow_type(self) -> None:
        agent = _make_agent()
        inp = Nis2ObligationsPresetInput(
            context=EnterpriseContext(tenant_id="ref-t"),
            entity_role="Betreiber wesentlicher Dienste",
        )

        result = run_nis2_obligations_preset(inp, agent=agent)

        assert result.machine.ref_ids.get("flow_type") == "nis2_obligations"


# ---------------------------------------------------------------------------
# Idempotency at preset level
# ---------------------------------------------------------------------------


class TestPresetIdempotency:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_same_request_id_returns_cached(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(tenant_id="idem-t"),
            use_case_description="Idempotenz-Test KI-System",
            request_id="REQ-IDEM-001",
        )

        r1 = run_eu_ai_act_risk_preset(inp, agent=agent)
        r2 = run_eu_ai_act_risk_preset(inp, agent=agent)

        assert r2.meta.is_cached is True
        assert r1.human.answer_de == r2.human.answer_de

    def test_no_request_id_no_caching(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(tenant_id="idem-t"),
            use_case_description="Kein Request-ID Test",
        )

        r1 = run_eu_ai_act_risk_preset(inp, agent=agent)
        r2 = run_eu_ai_act_risk_preset(inp, agent=agent)

        assert r1.meta.is_cached is not True
        assert r2.meta.is_cached is not True


# ---------------------------------------------------------------------------
# Channel + DATEV/SAP formatting
# ---------------------------------------------------------------------------


class TestChannelFormatting:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_datev_channel_passes_structured_answer(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(
                tenant_id="datev-t",
                client_id="mandant-99",
            ),
            use_case_description="KI-Bilanzanalyse für DATEV",
            channel=AdvisorChannel.datev,
            channel_metadata=ChannelMetadata(
                datev_client_number="99",
            ),
        )

        result = run_eu_ai_act_risk_preset(inp, agent=agent)

        assert result.meta.channel == AdvisorChannel.datev
        assert "Schlagworte:" in result.human.answer_de

    def test_sap_channel_with_document_id(self) -> None:
        agent = _make_agent()
        inp = Nis2ObligationsPresetInput(
            context=EnterpriseContext(
                tenant_id="sap-t",
                system_id="WERK-SUED",
            ),
            entity_role="KRITIS-naher Zulieferer",
            channel=AdvisorChannel.sap,
            channel_metadata=ChannelMetadata(
                sap_document_id="SAP-DOC-123",
            ),
        )

        result = run_nis2_obligations_preset(inp, agent=agent)

        assert result.meta.channel == AdvisorChannel.sap
        ref = result.machine.ref_ids
        assert ref.get("sap_document_id") == "SAP-DOC-123"
        assert ref.get("system_id") == "WERK-SUED"


# ---------------------------------------------------------------------------
# Flow type in metrics
# ---------------------------------------------------------------------------


class TestFlowTypeMetrics:
    def setup_method(self) -> None:
        clear_evidence()
        clear_idem()

    def teardown_method(self) -> None:
        clear_evidence()
        clear_idem()

    def test_flow_type_tracked_in_metrics(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(tenant_id="ft-t"),
            use_case_description="Flow-Type Tracking Test",
        )
        run_eu_ai_act_risk_preset(inp, agent=agent)

        metrics = aggregate_advisor_metrics(tenant_id="ft-t")
        assert (
            metrics.flow_type_distribution.get(
                "eu_ai_act_risk_assessment",
                0,
            )
            >= 1
        )
