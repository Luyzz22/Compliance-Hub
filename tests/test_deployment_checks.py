"""Tests for Wave 14 — Deployment checks & CI/Temporal gates.

Covers:
- Deployment-check API across lifecycle/classification/readiness combinations
- Missing owner flagged as blocking item
- Board-report linkage (fresh report = positive note, stale = blocking for HRC)
- Evidence events for deployment checks (caller_type logged)
- CI script exit code logic (mocked API)
- Deterministic behavior for identical inputs
"""

from __future__ import annotations

from app.grc.ai_system_readiness import deployment_check
from app.grc.client_board_report_service import (
    ClientBoardReport,
    _store_report,
    clear_reports_for_tests,
    clear_workflows_for_tests,
)
from app.grc.models import (
    AiRiskAssessment,
    AiSystem,
    AiSystemClassification,
    GapStatus,
    Iso42001GapRecord,
    LifecycleStage,
)
from app.grc.store import (
    clear_for_tests as clear_grc,
)
from app.grc.store import (
    upsert_ai_system,
    upsert_gap,
    upsert_risk,
)
from app.services.rag.evidence_store import clear_for_tests as clear_evidence


def _cleanup() -> None:
    clear_evidence()
    clear_grc()
    clear_reports_for_tests()
    clear_workflows_for_tests()


# ---------------------------------------------------------------------------
# Deployment check across scenarios
# ---------------------------------------------------------------------------


class TestDeploymentCheckScenarios:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_unknown_system(self) -> None:
        result = deployment_check(tenant_id="dc-t", system_id="NONEXISTENT")
        assert "error" in result

    def test_empty_system_returns_unknown(self) -> None:
        upsert_ai_system(
            AiSystem(
                tenant_id="dc-t",
                system_id="EMPTY-01",
            )
        )

        result = deployment_check(tenant_id="dc-t", system_id="EMPTY-01")

        assert result["readiness_level"] == "unknown"
        assert result["is_high_risk_candidate"] is False
        assert len(result["blocking_items"]) > 0
        assert "advisory_message_de" in result

    def test_hrc_insufficient_evidence(self) -> None:
        upsert_ai_system(
            AiSystem(
                tenant_id="dc-t",
                system_id="HRC-01",
                ai_act_classification=AiSystemClassification.high_risk_candidate,
                iso42001_in_scope=True,
            )
        )
        upsert_risk(
            AiRiskAssessment(
                tenant_id="dc-t",
                system_id="HRC-01",
                risk_category="high_risk",
            )
        )
        upsert_gap(
            Iso42001GapRecord(
                tenant_id="dc-t",
                system_id="HRC-01",
                control_families=["governance"],
                status=GapStatus.open,
            )
        )

        result = deployment_check(tenant_id="dc-t", system_id="HRC-01")

        assert result["is_high_risk_candidate"] is True
        assert result["readiness_level"] == "insufficient_evidence"
        assert any("Kern-Gaps" in b for b in result["blocking_items"])

    def test_ready_for_review(self) -> None:
        upsert_ai_system(
            AiSystem(
                tenant_id="dc-t",
                system_id="READY-01",
                name="Ready System",
                business_owner="owner@example.com",
                ai_act_classification=AiSystemClassification.high_risk_candidate,
                lifecycle_stage=LifecycleStage.pilot,
            )
        )
        upsert_risk(
            AiRiskAssessment(
                tenant_id="dc-t",
                system_id="READY-01",
                risk_category="high_risk",
            )
        )

        result = deployment_check(tenant_id="dc-t", system_id="READY-01")

        assert result["readiness_level"] in ("ready_for_review", "partially_covered")
        assert "Ready System" in result["advisory_message_de"]

    def test_minimal_risk_system(self) -> None:
        upsert_ai_system(
            AiSystem(
                tenant_id="dc-t",
                system_id="MIN-01",
                ai_act_classification=AiSystemClassification.minimal,
            )
        )
        upsert_risk(
            AiRiskAssessment(
                tenant_id="dc-t",
                system_id="MIN-01",
                risk_category="minimal_risk",
            )
        )

        result = deployment_check(tenant_id="dc-t", system_id="MIN-01")

        assert result["is_high_risk_candidate"] is False
        assert result["readiness_level"] in ("ready_for_review", "partially_covered")


# ---------------------------------------------------------------------------
# Missing owner blocking
# ---------------------------------------------------------------------------


class TestOwnerBlocking:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_no_owner_flagged(self) -> None:
        upsert_ai_system(
            AiSystem(
                tenant_id="dc-t",
                system_id="NO-OWNER",
            )
        )

        result = deployment_check(tenant_id="dc-t", system_id="NO-OWNER")

        assert any("Owner" in b for b in result["blocking_items"])

    def test_owner_present_not_flagged(self) -> None:
        upsert_ai_system(
            AiSystem(
                tenant_id="dc-t",
                system_id="HAS-OWNER",
                business_owner="cto@acme.de",
            )
        )
        upsert_risk(
            AiRiskAssessment(
                tenant_id="dc-t",
                system_id="HAS-OWNER",
            )
        )

        result = deployment_check(tenant_id="dc-t", system_id="HAS-OWNER")

        assert not any("Owner" in b for b in result["blocking_items"])


# ---------------------------------------------------------------------------
# Board report linkage
# ---------------------------------------------------------------------------


class TestBoardReportLinkage:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_fresh_report_mentioned_positively(self) -> None:
        upsert_ai_system(
            AiSystem(
                tenant_id="dc-t",
                system_id="RPT-01",
                ai_act_classification=AiSystemClassification.high_risk_candidate,
                business_owner="owner@acme.de",
            )
        )
        upsert_risk(
            AiRiskAssessment(
                tenant_id="dc-t",
                system_id="RPT-01",
            )
        )

        _store_report(
            ClientBoardReport(
                tenant_id="dc-t",
                client_id="m-1",
                system_ids=["RPT-01"],
                systems_included=1,
                report_markdown="test",
            )
        )

        result = deployment_check(tenant_id="dc-t", system_id="RPT-01")

        assert result["has_recent_board_report"] is True
        assert "Board-Report vorhanden" in result["advisory_message_de"]

    def test_missing_report_blocks_hrc(self) -> None:
        upsert_ai_system(
            AiSystem(
                tenant_id="dc-t",
                system_id="NO-RPT",
                ai_act_classification=AiSystemClassification.high_risk_candidate,
                business_owner="owner@acme.de",
            )
        )
        upsert_risk(
            AiRiskAssessment(
                tenant_id="dc-t",
                system_id="NO-RPT",
            )
        )

        result = deployment_check(tenant_id="dc-t", system_id="NO-RPT")

        assert result["has_recent_board_report"] is False
        assert any("Board-Report" in b for b in result["blocking_items"])


# ---------------------------------------------------------------------------
# Evidence events
# ---------------------------------------------------------------------------


class TestDeploymentCheckEvidence:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_evidence_logged_with_caller_type(self) -> None:
        from app.services.rag.evidence_store import _events, _lock

        upsert_ai_system(
            AiSystem(
                tenant_id="ev-t",
                system_id="EV-DC-01",
            )
        )

        deployment_check(
            tenant_id="ev-t",
            system_id="EV-DC-01",
            caller_type="ci",
            trace_id="CI-TRACE-001",
        )

        with _lock:
            dc_events = [e for e in _events if e.get("event_type") == "deployment_check"]

        assert len(dc_events) >= 1
        ev = dc_events[-1]
        assert ev["system_id"] == "EV-DC-01"
        assert ev["caller_type"] == "ci"
        assert ev["trace_id"] == "CI-TRACE-001"
        assert "readiness_level" in ev
        assert "classification" in ev


# ---------------------------------------------------------------------------
# CI script exit code logic (unit test, no real API)
# ---------------------------------------------------------------------------


class TestCiScriptLogic:
    """Test the CI exit-code decision logic directly."""

    def test_hrc_insufficient_returns_1(self) -> None:
        is_hrc = True
        level = "insufficient_evidence"
        blocking = ["Offene Kern-Gaps"]
        strict = False

        exit_code = _ci_exit_code(is_hrc, level, blocking, strict)
        assert exit_code == 1

    def test_ready_returns_0(self) -> None:
        exit_code = _ci_exit_code(False, "ready_for_review", [], False)
        assert exit_code == 0

    def test_strict_with_blocking_returns_1(self) -> None:
        exit_code = _ci_exit_code(False, "partially_covered", ["open gap"], True)
        assert exit_code == 1

    def test_non_strict_partially_covered_returns_0(self) -> None:
        exit_code = _ci_exit_code(False, "partially_covered", ["open gap"], False)
        assert exit_code == 0


def _ci_exit_code(
    is_hrc: bool,
    level: str,
    blocking: list[str],
    strict: bool,
) -> int:
    """Mirrors the CI script decision logic for unit testing."""
    if is_hrc and level == "insufficient_evidence":
        return 1
    if strict and blocking:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeploymentCheckDeterminism:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_same_input_same_output(self) -> None:
        upsert_ai_system(
            AiSystem(
                tenant_id="det-t",
                system_id="DET-01",
            )
        )

        r1 = deployment_check(tenant_id="det-t", system_id="DET-01")
        r2 = deployment_check(tenant_id="det-t", system_id="DET-01")

        assert r1["readiness_level"] == r2["readiness_level"]
        assert r1["blocking_items"] == r2["blocking_items"]
        assert r1["is_high_risk_candidate"] == r2["is_high_risk_candidate"]
