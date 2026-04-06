"""Tests for Wave 10 — GRC records from advisor presets.

Covers:
- Mapping from each preset type → GRC entity
- Idempotent upsert (same context → update, not duplicate)
- End-to-end: preset call → GRC record persisted → evidence event
- Escalated/errored results → no GRC record created
- GRC store CRUD operations
- Evidence traceability linking
"""

from __future__ import annotations

from app.advisor.channels import AdvisorChannel
from app.advisor.enterprise_context import EnterpriseContext
from app.advisor.idempotency import clear_for_tests as clear_idem
from app.advisor.preset_models import (
    AiActRiskPresetInput,
    Iso42001GapCheckPresetInput,
    Nis2ObligationsPresetInput,
)
from app.advisor.preset_service import (
    run_eu_ai_act_risk_preset,
    run_iso42001_gap_preset,
    run_nis2_obligations_preset,
)
from app.grc.store import (
    clear_for_tests as clear_grc,
)
from app.grc.store import (
    list_iso42001_gaps,
    list_nis2_obligations,
    list_risks,
)
from app.services.agents.advisor_compliance_agent import AdvisorComplianceAgent
from app.services.rag.config import RAGConfig
from app.services.rag.corpus import Document
from app.services.rag.evidence_store import (
    clear_for_tests as clear_evidence,
)
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.llm import LlmCallContext, LlmResponse

MOCK_CORPUS = [
    Document(
        doc_id="g-1",
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
        doc_id="g-2",
        title="NIS2 Art. 21 Risikomanagement",
        content=(
            "Wesentliche Einrichtungen müssen Risikomanagement, "
            "Meldepflichten (24 Stunden Frühwarnung, 72 Stunden "
            "Vorfallmeldung) und Governance-Maßnahmen umsetzen. "
            "KRITIS-nahe Zulieferer in der Lieferkette."
        ),
        source="NIS2",
        section="Art. 21",
    ),
    Document(
        doc_id="g-3",
        title="ISO 42001 Governance",
        content=(
            "ISO 42001 erfordert Governance, Risikobewertung, "
            "Datenmanagement, Monitoring und Transparenz. "
            "ISO 27001 bietet erhebliche Überschneidungen."
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
        model_id="mock",
        input_tokens=50,
        output_tokens=30,
    )


def _make_agent() -> AdvisorComplianceAgent:
    config = RAGConfig(retrieval_mode="bm25")
    retriever = HybridRetriever(MOCK_CORPUS, config)
    return AdvisorComplianceAgent(retriever=retriever, llm_fn=_mock_llm)


def _cleanup() -> None:
    clear_evidence()
    clear_idem()
    clear_grc()


# ---------------------------------------------------------------------------
# Preset → GRC record creation
# ---------------------------------------------------------------------------


class TestPresetCreatesGrcRecord:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_ai_act_preset_creates_risk_record(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(
                tenant_id="grc-t",
                client_id="m-1",
                system_id="AI-01",
            ),
            use_case_description="KI-Kreditwürdigkeitsprüfung",
        )

        result = run_eu_ai_act_risk_preset(inp, agent=agent)

        risks = list_risks(tenant_id="grc-t")
        assert len(risks) == 1
        r = risks[0]
        assert r.tenant_id == "grc-t"
        assert r.client_id == "m-1"
        assert r.system_id == "AI-01"
        assert r.source_preset_type == "eu_ai_act_risk_assessment"
        assert r.risk_category in (
            "high_risk",
            "limited_risk",
            "minimal_risk",
            "unclassified",
        )
        assert r.status == "open"
        assert "grc_record_id" in result.machine.ref_ids

    def test_nis2_preset_creates_obligation_record(self) -> None:
        agent = _make_agent()
        inp = Nis2ObligationsPresetInput(
            context=EnterpriseContext(
                tenant_id="grc-t",
                system_id="WERK-1",
            ),
            entity_role="KRITIS-naher Zulieferer",
            sector="Energie",
        )

        result = run_nis2_obligations_preset(inp, agent=agent)

        records = list_nis2_obligations(tenant_id="grc-t")
        assert len(records) == 1
        r = records[0]
        assert r.tenant_id == "grc-t"
        assert r.system_id == "WERK-1"
        assert r.source_preset_type == "nis2_obligations"
        assert r.entity_role == "KRITIS-naher Zulieferer"
        assert "grc_record_id" in result.machine.ref_ids

    def test_iso42001_preset_creates_gap_record(self) -> None:
        agent = _make_agent()
        inp = Iso42001GapCheckPresetInput(
            context=EnterpriseContext(
                tenant_id="grc-t",
                system_id="PLAT-01",
            ),
            current_measures=("ISO 27001 zertifiziert, kein formales KI-Governance-Framework"),
        )

        result = run_iso42001_gap_preset(inp, agent=agent)

        gaps = list_iso42001_gaps(tenant_id="grc-t")
        assert len(gaps) == 1
        g = gaps[0]
        assert g.tenant_id == "grc-t"
        assert g.source_preset_type == "iso42001_gap_check"
        assert "grc_record_id" in result.machine.ref_ids


# ---------------------------------------------------------------------------
# Idempotent upsert
# ---------------------------------------------------------------------------


class TestIdempotentUpsert:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_same_context_updates_not_duplicates(self) -> None:
        agent = _make_agent()
        ctx = EnterpriseContext(
            tenant_id="idem-t",
            client_id="m-42",
            system_id="SYS-1",
        )

        inp1 = AiActRiskPresetInput(
            context=ctx,
            use_case_description="Erste Bewertung Kreditprüfung",
        )
        run_eu_ai_act_risk_preset(inp1, agent=agent)

        inp2 = AiActRiskPresetInput(
            context=ctx,
            use_case_description="Aktualisierte Bewertung Kreditprüfung",
        )
        run_eu_ai_act_risk_preset(inp2, agent=agent)

        risks = list_risks(tenant_id="idem-t")
        assert len(risks) == 1

    def test_different_context_creates_separate_records(self) -> None:
        agent = _make_agent()

        inp1 = AiActRiskPresetInput(
            context=EnterpriseContext(
                tenant_id="idem-t",
                system_id="SYS-A",
            ),
            use_case_description="System A Bewertung",
        )
        run_eu_ai_act_risk_preset(inp1, agent=agent)

        inp2 = AiActRiskPresetInput(
            context=EnterpriseContext(
                tenant_id="idem-t",
                system_id="SYS-B",
            ),
            use_case_description="System B Bewertung",
        )
        run_eu_ai_act_risk_preset(inp2, agent=agent)

        risks = list_risks(tenant_id="idem-t")
        assert len(risks) == 2


# ---------------------------------------------------------------------------
# Evidence traceability
# ---------------------------------------------------------------------------


class TestEvidenceTraceability:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_grc_event_in_evidence_store(self) -> None:
        from app.services.rag.evidence_store import _events, _lock

        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(tenant_id="ev-t"),
            use_case_description="Evidence-Link Test",
            trace_id="TRACE-001",
        )
        run_eu_ai_act_risk_preset(inp, agent=agent)

        with _lock:
            grc_events = [e for e in _events if e.get("event_type") == "grc_record_created"]

        assert len(grc_events) >= 1
        ev = grc_events[-1]
        assert ev["tenant_id"] == "ev-t"
        assert ev["flow_type"] == "eu_ai_act_risk_assessment"
        assert ev["grc_record_id"].startswith("RISK-")

    def test_grc_record_id_in_preset_response(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(tenant_id="ref-t"),
            use_case_description="Ref-ID propagation test",
        )
        result = run_eu_ai_act_risk_preset(inp, agent=agent)

        grc_id = result.machine.ref_ids.get("grc_record_id")
        assert grc_id is not None
        assert grc_id.startswith("RISK-")


# ---------------------------------------------------------------------------
# Escalated / errored → no GRC record
# ---------------------------------------------------------------------------


class TestNoGrcOnEscalation:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_out_of_scope_query_no_grc_record(self) -> None:
        config = RAGConfig(retrieval_mode="bm25")
        retriever = HybridRetriever(MOCK_CORPUS, config)
        agent = AdvisorComplianceAgent(retriever=retriever)

        inp = AiActRiskPresetInput(
            context=EnterpriseContext(tenant_id="esc-t"),
            use_case_description=(
                "Wie wird das Wetter morgen in München? Das ist keine Compliance-Frage."
            ),
        )
        result = run_eu_ai_act_risk_preset(inp, agent=agent)

        assert result.human.is_escalated is True
        risks = list_risks(tenant_id="esc-t")
        assert len(risks) == 0


# ---------------------------------------------------------------------------
# GRC store filtering
# ---------------------------------------------------------------------------


class TestGrcStoreFiltering:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_filter_by_client_id(self) -> None:
        agent = _make_agent()
        for cid in ["mandant-1", "mandant-2"]:
            inp = Nis2ObligationsPresetInput(
                context=EnterpriseContext(
                    tenant_id="filter-t",
                    client_id=cid,
                ),
                entity_role="Digitaler Dienstleister",
            )
            run_nis2_obligations_preset(inp, agent=agent)

        all_recs = list_nis2_obligations(tenant_id="filter-t")
        assert len(all_recs) == 2

        m1 = list_nis2_obligations(
            tenant_id="filter-t",
            client_id="mandant-1",
        )
        assert len(m1) == 1
        assert m1[0].client_id == "mandant-1"

    def test_filter_by_control_family(self) -> None:
        agent = _make_agent()
        inp = Iso42001GapCheckPresetInput(
            context=EnterpriseContext(tenant_id="filter-t"),
            current_measures="ISMS ISO 27001, keine KI-Governance",
        )
        run_iso42001_gap_preset(inp, agent=agent)

        all_gaps = list_iso42001_gaps(tenant_id="filter-t")
        assert len(all_gaps) >= 1

        if all_gaps[0].control_families:
            fam = all_gaps[0].control_families[0]
            filtered = list_iso42001_gaps(
                tenant_id="filter-t",
                control_family=fam,
            )
            assert len(filtered) >= 1


# ---------------------------------------------------------------------------
# Cross-channel GRC record creation
# ---------------------------------------------------------------------------


class TestCrossChannel:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_datev_channel_creates_grc_record(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(
                tenant_id="datev-grc",
                client_id="mandant-55",
            ),
            use_case_description="DATEV-Mandant KI-Bewertung",
            channel=AdvisorChannel.datev,
        )
        run_eu_ai_act_risk_preset(inp, agent=agent)

        risks = list_risks(
            tenant_id="datev-grc",
            client_id="mandant-55",
        )
        assert len(risks) == 1
        assert risks[0].client_id == "mandant-55"
