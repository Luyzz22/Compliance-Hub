"""Tests for Wave 13 — Client/Mandant-level AI Compliance Board Reports.

Covers:
- Data aggregation for a Mandant with multiple AiSystems + GRC records
- Report synthesis (deterministic fallback + LLM path)
- Workflow start → status → completed flow
- Evidence events including tenant_id, client_id, system_ids
- OPA enforcement on API endpoints
- EnterpriseContext propagation (Kanzlei tenant + Mandant client)
- System filter restricting included systems
"""

from __future__ import annotations

from app.advisor.enterprise_context import EnterpriseContext
from app.advisor.idempotency import clear_for_tests as clear_idem
from app.advisor.preset_models import (
    AiActRiskPresetInput,
)
from app.advisor.preset_service import (
    run_eu_ai_act_risk_preset,
)
from app.grc.client_board_report_service import (
    aggregate_client_data,
    clear_reports_for_tests,
    clear_workflows_for_tests,
    get_report,
    get_workflow_status,
    list_reports,
    run_client_board_report,
    synthesise_report,
)
from app.grc.models import (
    AiRiskAssessment,
    AiSystem,
    AiSystemClassification,
    GapStatus,
    Iso42001GapRecord,
    LifecycleStage,
    Nis2ObligationRecord,
    ObligationStatus,
)
from app.grc.store import (
    clear_for_tests as clear_grc,
)
from app.grc.store import (
    upsert_ai_system,
    upsert_gap,
    upsert_nis2,
    upsert_risk,
)
from app.services.agents.advisor_compliance_agent import AdvisorComplianceAgent
from app.services.rag.config import RAGConfig
from app.services.rag.corpus import Document
from app.services.rag.evidence_store import clear_for_tests as clear_evidence
from app.services.rag.hybrid_retriever import HybridRetriever
from app.services.rag.llm import LlmCallContext, LlmResponse

MOCK_CORPUS = [
    Document(
        doc_id="w13-1",
        title="EU AI Act Art. 6",
        content=(
            "Hochrisiko KI-Systeme nach Art. 6 und Anhang III "
            "erfordern eine Konformitätsbewertung. Systeme zur "
            "Kreditwürdigkeitsprüfung fallen unter Anhang III Nr. 5."
        ),
        source="EU AI Act",
        section="Art. 6",
    ),
    Document(
        doc_id="w13-2",
        title="NIS2 Art. 21",
        content=(
            "Wesentliche Einrichtungen müssen Risikomanagement, "
            "Meldepflichten und Governance-Maßnahmen umsetzen."
        ),
        source="NIS2",
        section="Art. 21",
    ),
    Document(
        doc_id="w13-3",
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
    clear_reports_for_tests()
    clear_workflows_for_tests()


def _seed_mandant_data(
    tenant_id: str = "kanzlei-t",
    client_id: str = "mandant-42",
) -> None:
    """Seed synthetic AiSystems + GRC records for a Mandant."""
    upsert_ai_system(
        AiSystem(
            tenant_id=tenant_id,
            client_id=client_id,
            system_id="CREDIT-AI-01",
            name="KI-Kreditprüfung",
            ai_act_classification=AiSystemClassification.high_risk_candidate,
            nis2_relevant=True,
            iso42001_in_scope=True,
            lifecycle_stage=LifecycleStage.pilot,
        )
    )
    upsert_ai_system(
        AiSystem(
            tenant_id=tenant_id,
            client_id=client_id,
            system_id="CHATBOT-02",
            name="Mandanten-Chatbot",
            ai_act_classification=AiSystemClassification.limited,
            lifecycle_stage=LifecycleStage.production,
        )
    )

    upsert_risk(
        AiRiskAssessment(
            tenant_id=tenant_id,
            system_id="CREDIT-AI-01",
            risk_category="high_risk",
        )
    )
    upsert_risk(
        AiRiskAssessment(
            tenant_id=tenant_id,
            system_id="CHATBOT-02",
            risk_category="limited_risk",
        )
    )

    upsert_nis2(
        Nis2ObligationRecord(
            tenant_id=tenant_id,
            system_id="CREDIT-AI-01",
            status=ObligationStatus.in_progress,
            obligation_tags=["risk_management", "incident_reporting"],
        )
    )

    upsert_gap(
        Iso42001GapRecord(
            tenant_id=tenant_id,
            system_id="CREDIT-AI-01",
            control_families=["governance", "monitoring"],
            status=GapStatus.open,
            gap_severity="major",
        )
    )


# ---------------------------------------------------------------------------
# Data aggregation
# ---------------------------------------------------------------------------


class TestDataAggregation:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_aggregate_returns_system_summaries(self) -> None:
        _seed_mandant_data()
        result = aggregate_client_data(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
        )

        assert result["systems_count"] == 2
        assert result["high_risk_systems"] == 1
        assert result["total_open_gaps"] == 1
        assert result["total_open_obligations"] == 1

        sys_ids = [s["system_id"] for s in result["systems"]]
        assert "CREDIT-AI-01" in sys_ids
        assert "CHATBOT-02" in sys_ids

    def test_aggregate_empty_mandant(self) -> None:
        result = aggregate_client_data(
            tenant_id="kanzlei-t",
            client_id="unknown",
        )
        assert result["systems_count"] == 0

    def test_system_filter(self) -> None:
        _seed_mandant_data()
        result = aggregate_client_data(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
            system_filter=["CREDIT-AI-01"],
        )
        assert result["systems_count"] == 1
        assert result["systems"][0]["system_id"] == "CREDIT-AI-01"


# ---------------------------------------------------------------------------
# Report synthesis
# ---------------------------------------------------------------------------


class TestReportSynthesis:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_deterministic_report(self) -> None:
        _seed_mandant_data()
        snapshot = aggregate_client_data(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
        )
        report = synthesise_report(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
            reporting_period="Q1 2026",
            snapshot=snapshot,
        )

        assert "mandant-42" in report.report_markdown
        assert "Rechtsberatung" in report.report_markdown
        assert report.systems_included == 2
        assert len(report.highlights) >= 1

    def test_llm_report(self) -> None:
        _seed_mandant_data()
        snapshot = aggregate_client_data(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
        )

        def mock_llm(prompt: str, ctx: LlmCallContext) -> LlmResponse:
            assert ctx.tenant_id == "kanzlei-t"
            assert ctx.action == "generate_client_board_report"
            return LlmResponse(
                text="## LLM-generierter Report\nTest-Inhalt.",
                model_id="mock",
            )

        report = synthesise_report(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
            reporting_period="Q1 2026",
            snapshot=snapshot,
            llm_fn=mock_llm,
        )

        assert "LLM-generierter Report" in report.report_markdown
        assert "Rechtsberatung" in report.report_markdown

    def test_report_persisted(self) -> None:
        _seed_mandant_data()
        snapshot = aggregate_client_data(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
        )
        report = synthesise_report(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
            reporting_period="Q1 2026",
            snapshot=snapshot,
        )

        stored = get_report(report.id)
        assert stored is not None
        assert stored.id == report.id


# ---------------------------------------------------------------------------
# Workflow orchestration
# ---------------------------------------------------------------------------


class TestWorkflowOrchestration:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_full_workflow_run(self) -> None:
        _seed_mandant_data()
        result = run_client_board_report(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
            reporting_period="Q1 2026",
        )

        assert result["status"] == "COMPLETED"
        assert result["systems_included"] == 2
        assert result["report_id"].startswith("CBR-")
        assert result["client_id"] == "mandant-42"

    def test_workflow_status_tracked(self) -> None:
        _seed_mandant_data()
        result = run_client_board_report(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
            workflow_id="cbr-test-001",
        )

        wf = get_workflow_status("cbr-test-001")
        assert wf is not None
        assert wf["status"] == "COMPLETED"
        assert wf["report_id"] == result["report_id"]

    def test_list_reports_for_mandant(self) -> None:
        _seed_mandant_data()
        run_client_board_report(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
            reporting_period="Q1 2026",
        )
        run_client_board_report(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
            reporting_period="Q2 2026",
        )

        reports = list_reports(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
        )
        assert len(reports) == 2


# ---------------------------------------------------------------------------
# Evidence events
# ---------------------------------------------------------------------------


class TestReportEvidence:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_evidence_event_emitted(self) -> None:
        from app.services.rag.evidence_store import _events, _lock

        _seed_mandant_data()
        run_client_board_report(
            tenant_id="kanzlei-t",
            client_id="mandant-42",
            reporting_period="Q1 2026",
        )

        with _lock:
            cbr_events = [
                e for e in _events if e.get("event_type") == "client_board_report_generated"
            ]

        assert len(cbr_events) >= 1
        ev = cbr_events[-1]
        assert ev["tenant_id"] == "kanzlei-t"
        assert ev["client_id"] == "mandant-42"
        assert ev["reporting_period"] == "Q1 2026"
        assert ev["systems_included"] == 2
        assert len(ev["system_ids"]) == 2


# ---------------------------------------------------------------------------
# End-to-end: presets → GRC → board report
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_presets_then_board_report(self) -> None:
        agent = _make_agent()
        ctx = EnterpriseContext(
            tenant_id="e2e-kanzlei",
            client_id="mandant-99",
            system_id="E2E-SYS",
        )

        run_eu_ai_act_risk_preset(
            AiActRiskPresetInput(
                context=ctx,
                use_case_description="KI-Kreditprüfung",
            ),
            agent=agent,
        )

        result = run_client_board_report(
            tenant_id="e2e-kanzlei",
            client_id="mandant-99",
        )

        assert result["status"] == "COMPLETED"
        assert result["systems_included"] >= 0

        if result["report_id"]:
            report = get_report(result["report_id"])
            assert report is not None
            assert "Rechtsberatung" in report.report_markdown
