"""Tests for Wave 11 — AI System Inventory & cross-framework mapping.

Covers:
- Auto-creation of AiSystem stubs from GRC records
- AiSystem classification updates from risk presets (high_risk_candidate, never auto high_risk)
- NIS2/ISO42001 scope flags propagation
- AI System overview API assembling data from multiple GRC entities
- Framework mapping returning correct touched controls/articles
- Evidence events including ai_system_id
- Idempotent AiSystem upsert
"""

from __future__ import annotations

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
from app.grc.framework_mapping import (
    aggregate_framework_coverage,
    build_system_overview_hints,
    touched_controls_for_gap,
    touched_controls_for_nis2,
    touched_controls_for_risk,
)
from app.grc.models import AiSystemClassification
from app.grc.store import (
    clear_for_tests as clear_grc,
)
from app.grc.store import (
    get_ai_system,
    get_or_create_ai_system,
    list_ai_systems,
    list_iso42001_gaps,
    list_nis2_obligations,
    list_risks,
    upsert_ai_system,
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
        doc_id="w11-1",
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
        doc_id="w11-2",
        title="NIS2 Art. 21 Risikomanagement",
        content=(
            "Wesentliche Einrichtungen müssen Risikomanagement, "
            "Meldepflichten (24 Stunden Frühwarnung, 72 Stunden "
            "Vorfallmeldung) und Governance-Maßnahmen umsetzen."
        ),
        source="NIS2",
        section="Art. 21",
    ),
    Document(
        doc_id="w11-3",
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
# AI System auto-creation from GRC records
# ---------------------------------------------------------------------------


class TestAiSystemAutoCreation:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_risk_preset_auto_creates_ai_system(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(
                tenant_id="sys-t",
                client_id="m-1",
                system_id="AI-CREDIT-01",
            ),
            use_case_description="KI-Kreditwürdigkeitsprüfung",
        )

        run_eu_ai_act_risk_preset(inp, agent=agent)

        ai_sys = get_ai_system(tenant_id="sys-t", system_id="AI-CREDIT-01")
        assert ai_sys is not None
        assert ai_sys.tenant_id == "sys-t"
        assert ai_sys.system_id == "AI-CREDIT-01"
        assert ai_sys.auto_created is True

    def test_nis2_preset_auto_creates_ai_system_with_nis2_flag(self) -> None:
        agent = _make_agent()
        inp = Nis2ObligationsPresetInput(
            context=EnterpriseContext(
                tenant_id="sys-t",
                system_id="INFRA-01",
            ),
            entity_role="KRITIS-naher Zulieferer",
            sector="Energie",
        )

        run_nis2_obligations_preset(inp, agent=agent)

        ai_sys = get_ai_system(tenant_id="sys-t", system_id="INFRA-01")
        assert ai_sys is not None
        assert ai_sys.nis2_relevant is True

    def test_iso42001_preset_auto_creates_ai_system_with_scope_flag(self) -> None:
        agent = _make_agent()
        inp = Iso42001GapCheckPresetInput(
            context=EnterpriseContext(
                tenant_id="sys-t",
                system_id="PLAT-01",
            ),
            current_measures="ISO 27001 zertifiziert, kein KI-Governance",
        )

        run_iso42001_gap_preset(inp, agent=agent)

        ai_sys = get_ai_system(tenant_id="sys-t", system_id="PLAT-01")
        assert ai_sys is not None
        assert ai_sys.iso42001_in_scope is True

    def test_no_system_id_no_ai_system_created(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(tenant_id="sys-t"),
            use_case_description="Test ohne system_id",
        )

        run_eu_ai_act_risk_preset(inp, agent=agent)

        systems = list_ai_systems(tenant_id="sys-t")
        assert len(systems) == 0


# ---------------------------------------------------------------------------
# Classification never auto-upgrades to high_risk
# ---------------------------------------------------------------------------


class TestClassificationGuardrails:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_risk_preset_sets_high_risk_candidate_not_high_risk(self) -> None:
        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(
                tenant_id="cls-t",
                system_id="AI-HR-01",
            ),
            use_case_description="KI-Kreditwürdigkeitsprüfung",
        )

        run_eu_ai_act_risk_preset(inp, agent=agent)

        ai_sys = get_ai_system(tenant_id="cls-t", system_id="AI-HR-01")
        assert ai_sys is not None
        assert ai_sys.ai_act_classification != AiSystemClassification.high_risk
        if ai_sys.ai_act_classification not in (
            AiSystemClassification.not_in_scope,
            AiSystemClassification.minimal,
            AiSystemClassification.limited,
        ):
            assert ai_sys.ai_act_classification == AiSystemClassification.high_risk_candidate


# ---------------------------------------------------------------------------
# AiSystem store operations
# ---------------------------------------------------------------------------


class TestAiSystemStore:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_get_or_create_idempotent(self) -> None:
        sys1 = get_or_create_ai_system(
            tenant_id="store-t",
            system_id="SYS-A",
        )
        sys2 = get_or_create_ai_system(
            tenant_id="store-t",
            system_id="SYS-A",
        )
        assert sys1.id == sys2.id

    def test_different_system_ids_create_separate(self) -> None:
        get_or_create_ai_system(tenant_id="store-t", system_id="SYS-A")
        get_or_create_ai_system(tenant_id="store-t", system_id="SYS-B")

        systems = list_ai_systems(tenant_id="store-t")
        assert len(systems) == 2

    def test_filter_by_classification(self) -> None:
        from app.grc.models import AiSystem

        upsert_ai_system(
            AiSystem(
                tenant_id="filt-t",
                system_id="S1",
                ai_act_classification=AiSystemClassification.high_risk_candidate,
            )
        )
        upsert_ai_system(
            AiSystem(
                tenant_id="filt-t",
                system_id="S2",
                ai_act_classification=AiSystemClassification.minimal,
            )
        )

        high = list_ai_systems(
            tenant_id="filt-t",
            classification="high_risk_candidate",
        )
        assert len(high) == 1
        assert high[0].system_id == "S1"

    def test_filter_by_nis2_relevant(self) -> None:
        from app.grc.models import AiSystem

        upsert_ai_system(
            AiSystem(
                tenant_id="filt-t",
                system_id="N1",
                nis2_relevant=True,
            )
        )
        upsert_ai_system(
            AiSystem(
                tenant_id="filt-t",
                system_id="N2",
                nis2_relevant=False,
            )
        )

        relevant = list_ai_systems(tenant_id="filt-t", nis2_relevant=True)
        assert len(relevant) == 1
        assert relevant[0].system_id == "N1"


# ---------------------------------------------------------------------------
# AI System overview assembles data
# ---------------------------------------------------------------------------


class TestAiSystemOverview:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_overview_assembles_multi_framework_data(self) -> None:
        agent = _make_agent()
        ctx = EnterpriseContext(
            tenant_id="ov-t",
            system_id="MULTI-01",
        )

        run_eu_ai_act_risk_preset(
            AiActRiskPresetInput(
                context=ctx,
                use_case_description="KI-Kreditwürdigkeitsprüfung",
            ),
            agent=agent,
        )

        run_nis2_obligations_preset(
            Nis2ObligationsPresetInput(
                context=ctx,
                entity_role="Digitaler Dienstleister",
            ),
            agent=agent,
        )

        run_iso42001_gap_preset(
            Iso42001GapCheckPresetInput(
                context=ctx,
                current_measures="ISO 27001 zertifiziert",
            ),
            agent=agent,
        )

        ai_sys = get_ai_system(tenant_id="ov-t", system_id="MULTI-01")
        assert ai_sys is not None

        risks = list_risks(tenant_id="ov-t", system_id="MULTI-01")
        nis2 = [r for r in list_nis2_obligations(tenant_id="ov-t") if r.system_id == "MULTI-01"]
        gaps = [g for g in list_iso42001_gaps(tenant_id="ov-t") if g.system_id == "MULTI-01"]

        assert len(risks) >= 1
        assert len(nis2) >= 1
        assert len(gaps) >= 1

        hints = build_system_overview_hints(
            risks=risks,
            nis2_records=nis2,
            gap_records=gaps,
        )
        assert "eu_ai_act" in hints or "nis2" in hints or "iso42001" in hints


# ---------------------------------------------------------------------------
# Framework mapping
# ---------------------------------------------------------------------------


class TestFrameworkMapping:
    def test_risk_high_returns_ai_act_articles(self) -> None:
        result = touched_controls_for_risk("high_risk")
        arts = result["eu_ai_act"]
        assert "Art. 6" in arts
        assert "Art. 9" in arts
        assert "Art. 43" in arts

    def test_risk_minimal_returns_art_69(self) -> None:
        result = touched_controls_for_risk("minimal_risk")
        assert "Art. 69" in result["eu_ai_act"]

    def test_nis2_obligations_map_to_articles(self) -> None:
        result = touched_controls_for_nis2(
            ["incident_reporting", "risk_management"],
            nis2_entity_type="essential",
        )
        arts = result["nis2"]
        assert "Art. 23(1)" in arts
        assert "Art. 21(1)" in arts

    def test_gap_families_map_to_iso42001_controls(self) -> None:
        result = touched_controls_for_gap(["governance", "data"])
        controls = result["iso42001"]
        assert "A.2.2" in controls
        assert "A.4.2" in controls

    def test_gap_with_iso27001_overlay(self) -> None:
        result = touched_controls_for_gap(
            ["governance"],
            iso27001_overlap=True,
        )
        assert "iso27001" in result
        assert "A.5.1" in result["iso27001"]

    def test_aggregate_multi_framework(self) -> None:
        merged = aggregate_framework_coverage(
            risk_categories=["high_risk"],
            obligation_tags=[["incident_reporting"]],
            gap_control_families=[["governance"]],
            has_iso27001_overlap=True,
        )
        assert "eu_ai_act" in merged
        assert "nis2" in merged
        assert "iso42001" in merged
        assert "iso27001" in merged


# ---------------------------------------------------------------------------
# Evidence traceability includes ai_system_id
# ---------------------------------------------------------------------------


class TestEvidenceAiSystemId:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_grc_evidence_includes_ai_system_id(self) -> None:
        from app.services.rag.evidence_store import _events, _lock

        agent = _make_agent()
        inp = AiActRiskPresetInput(
            context=EnterpriseContext(
                tenant_id="ev-sys-t",
                system_id="EV-SYS-01",
            ),
            use_case_description="Evidence mit AiSystem-Link",
        )

        run_eu_ai_act_risk_preset(inp, agent=agent)

        with _lock:
            grc_events = [e for e in _events if e.get("event_type") == "grc_record_created"]

        assert len(grc_events) >= 1
        ev = grc_events[-1]
        assert "ai_system_id" in ev
        assert ev["ai_system_id"].startswith("SYS-")


# ---------------------------------------------------------------------------
# Cross-preset linking to same AiSystem
# ---------------------------------------------------------------------------


class TestCrossPresetLinking:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_multiple_presets_link_to_same_ai_system(self) -> None:
        agent = _make_agent()
        ctx = EnterpriseContext(
            tenant_id="link-t",
            system_id="SHARED-01",
        )

        run_eu_ai_act_risk_preset(
            AiActRiskPresetInput(
                context=ctx,
                use_case_description="Bewertung 1",
            ),
            agent=agent,
        )

        run_nis2_obligations_preset(
            Nis2ObligationsPresetInput(
                context=ctx,
                entity_role="Wesentliche Einrichtung",
            ),
            agent=agent,
        )

        systems = list_ai_systems(tenant_id="link-t")
        assert len(systems) == 1

        ai_sys = systems[0]
        assert ai_sys.system_id == "SHARED-01"
        assert ai_sys.nis2_relevant is True
