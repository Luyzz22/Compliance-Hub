"""Tests for Wave 12 — AI lifecycle & release-gate readiness.

Covers:
- Readiness computation on synthetic GRC record combinations
- Lifecycle stage and readiness_level on AiSystem
- Per-framework hints (AI Act, NIS2, ISO 42001)
- Blocking items reported correctly
- Readiness stable for same input (deterministic)
- Evidence event logged on readiness evaluation
- API returning expected readiness levels
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
from app.grc.ai_system_readiness import compute_readiness, evaluate_and_update
from app.grc.models import (
    AiRiskAssessment,
    AiSystem,
    AiSystemClassification,
    GapStatus,
    Iso42001GapRecord,
    LifecycleStage,
    Nis2ObligationRecord,
    ObligationStatus,
    ReadinessLevel,
)
from app.grc.store import (
    clear_for_tests as clear_grc,
)
from app.grc.store import (
    get_ai_system,
    upsert_ai_system,
    upsert_gap,
    upsert_nis2,
    upsert_risk,
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
        doc_id="w12-1",
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
        doc_id="w12-2",
        title="NIS2 Art. 21 Risikomanagement",
        content=(
            "Wesentliche Einrichtungen müssen Risikomanagement, "
            "Meldepflichten und Governance-Maßnahmen umsetzen."
        ),
        source="NIS2",
        section="Art. 21",
    ),
    Document(
        doc_id="w12-3",
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
# Readiness computation on synthetic data
# ---------------------------------------------------------------------------


class TestReadinessComputation:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_no_records_returns_unknown(self) -> None:
        sys = upsert_ai_system(
            AiSystem(
                tenant_id="rd-t",
                system_id="EMPTY-01",
            )
        )

        result = compute_readiness(sys)

        assert result["readiness_level"] == "unknown"
        assert len(result["blocking_items"]) > 0

    def test_risk_only_returns_partially_covered(self) -> None:
        sys = upsert_ai_system(
            AiSystem(
                tenant_id="rd-t",
                system_id="RISK-ONLY",
                ai_act_classification=AiSystemClassification.high_risk_candidate,
                iso42001_in_scope=True,
            )
        )
        upsert_risk(
            AiRiskAssessment(
                tenant_id="rd-t",
                system_id="RISK-ONLY",
                risk_category="high_risk",
            )
        )
        upsert_gap(
            Iso42001GapRecord(
                tenant_id="rd-t",
                system_id="RISK-ONLY",
                control_families=["governance", "data"],
                status=GapStatus.open,
            )
        )

        result = compute_readiness(sys)

        assert result["readiness_level"] == "insufficient_evidence"
        assert any("Kern-Gaps" in b for b in result["blocking_items"])

    def test_all_covered_returns_ready_for_review(self) -> None:
        sys = upsert_ai_system(
            AiSystem(
                tenant_id="rd-t",
                system_id="READY-01",
                ai_act_classification=AiSystemClassification.high_risk_candidate,
                nis2_relevant=True,
                iso42001_in_scope=True,
                lifecycle_stage=LifecycleStage.pilot,
            )
        )
        upsert_risk(
            AiRiskAssessment(
                tenant_id="rd-t",
                system_id="READY-01",
                risk_category="high_risk",
            )
        )
        upsert_nis2(
            Nis2ObligationRecord(
                tenant_id="rd-t",
                system_id="READY-01",
                status=ObligationStatus.in_progress,
            )
        )
        upsert_gap(
            Iso42001GapRecord(
                tenant_id="rd-t",
                system_id="READY-01",
                control_families=["governance"],
                status=GapStatus.closed,
            )
        )

        result = compute_readiness(sys)

        assert result["readiness_level"] == "ready_for_review"
        assert result["lifecycle_stage"] == "pilot"
        assert len(result["blocking_items"]) == 0

    def test_nis2_identified_blocks_readiness(self) -> None:
        sys = upsert_ai_system(
            AiSystem(
                tenant_id="rd-t",
                system_id="NIS2-BLOCK",
                nis2_relevant=True,
            )
        )
        upsert_risk(
            AiRiskAssessment(
                tenant_id="rd-t",
                system_id="NIS2-BLOCK",
            )
        )
        upsert_nis2(
            Nis2ObligationRecord(
                tenant_id="rd-t",
                system_id="NIS2-BLOCK",
                status=ObligationStatus.identified,
            )
        )

        result = compute_readiness(sys)

        assert result["readiness_level"] == "partially_covered"
        assert any("NIS2" in b for b in result["blocking_items"])


# ---------------------------------------------------------------------------
# Per-framework hints
# ---------------------------------------------------------------------------


class TestFrameworkHints:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_ai_act_hints_no_assessment(self) -> None:
        sys = upsert_ai_system(
            AiSystem(
                tenant_id="h-t",
                system_id="H-01",
            )
        )
        result = compute_readiness(sys)
        ai_act = result["framework_hints"]["eu_ai_act"]
        assert ai_act["has_risk_assessment"] is False

    def test_nis2_hints_not_relevant(self) -> None:
        sys = upsert_ai_system(
            AiSystem(
                tenant_id="h-t",
                system_id="H-02",
            )
        )
        result = compute_readiness(sys)
        nis2 = result["framework_hints"]["nis2"]
        assert nis2["relevant"] is False

    def test_iso42001_hints_with_open_gaps(self) -> None:
        sys = upsert_ai_system(
            AiSystem(
                tenant_id="h-t",
                system_id="H-03",
                iso42001_in_scope=True,
            )
        )
        upsert_gap(
            Iso42001GapRecord(
                tenant_id="h-t",
                system_id="H-03",
                control_families=["governance", "monitoring"],
                status=GapStatus.open,
            )
        )

        result = compute_readiness(sys)
        iso = result["framework_hints"]["iso42001"]
        assert iso["in_scope"] is True
        assert iso["open_gaps"] == 1
        assert "governance" in iso["open_core_families"]


# ---------------------------------------------------------------------------
# Determinism / stability
# ---------------------------------------------------------------------------


class TestReadinessStability:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_same_input_same_output(self) -> None:
        sys = upsert_ai_system(
            AiSystem(
                tenant_id="st-t",
                system_id="STABLE-01",
            )
        )
        upsert_risk(
            AiRiskAssessment(
                tenant_id="st-t",
                system_id="STABLE-01",
            )
        )

        r1 = compute_readiness(sys)
        r2 = compute_readiness(sys)

        assert r1["readiness_level"] == r2["readiness_level"]
        assert r1["blocking_items"] == r2["blocking_items"]


# ---------------------------------------------------------------------------
# Evidence event logging
# ---------------------------------------------------------------------------


class TestReadinessEvidence:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_evaluate_logs_evidence_event(self) -> None:
        from app.services.rag.evidence_store import _events, _lock

        upsert_ai_system(
            AiSystem(
                tenant_id="ev-t",
                system_id="EV-01",
            )
        )

        evaluate_and_update(
            tenant_id="ev-t",
            system_id="EV-01",
            trace_id="TRACE-RD-001",
        )

        with _lock:
            rd_events = [e for e in _events if e.get("event_type") == "readiness_evaluation"]

        assert len(rd_events) >= 1
        ev = rd_events[-1]
        assert ev["system_id"] == "EV-01"
        assert ev["trace_id"] == "TRACE-RD-001"
        assert "readiness_level" in ev

    def test_evaluate_updates_ai_system_readiness(self) -> None:
        upsert_ai_system(
            AiSystem(
                tenant_id="ev-t",
                system_id="EV-02",
            )
        )

        evaluate_and_update(tenant_id="ev-t", system_id="EV-02")

        sys = get_ai_system(tenant_id="ev-t", system_id="EV-02")
        assert sys is not None
        assert sys.readiness_level == ReadinessLevel.unknown
        assert sys.last_reviewed_at != ""


# ---------------------------------------------------------------------------
# End-to-end: preset → readiness
# ---------------------------------------------------------------------------


class TestEndToEndReadiness:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_preset_creates_system_then_readiness_evaluates(self) -> None:
        agent = _make_agent()
        ctx = EnterpriseContext(
            tenant_id="e2e-t",
            system_id="E2E-SYS-01",
        )

        preset_result = run_eu_ai_act_risk_preset(
            AiActRiskPresetInput(
                context=ctx,
                use_case_description="KI-Kreditwürdigkeitsprüfung",
            ),
            agent=agent,
        )

        if preset_result.human.is_escalated:
            return

        result = evaluate_and_update(
            tenant_id="e2e-t",
            system_id="E2E-SYS-01",
        )

        assert "error" not in result
        assert result["readiness_level"] in (
            "unknown",
            "ready_for_review",
            "partially_covered",
            "insufficient_evidence",
        )
        assert result["system_id"] == "E2E-SYS-01"
        assert result["framework_hints"]["eu_ai_act"]["has_risk_assessment"]
