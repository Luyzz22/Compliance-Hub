"""Tests for Wave 16 — DACH Kanzlei & SAP reference flows.

Covers:
- Mandanten-Compliance-Dossier payload shape (snapshot tests)
- Period/version/schema tracking on jobs and artifacts
- Dossier dispatcher integration (build + DATEV connector)
- Mandant-export API trigger path
- Board-report → dossier auto-enqueue (feature-flagged)
- SAP S/4 CloudEvents inbound endpoint validation
- SAP inbound → AiSystem stub creation
- Evidence events for dossier exports and SAP inbound
"""

from __future__ import annotations

from app.grc.client_board_report_service import (
    clear_reports_for_tests,
    clear_workflows_for_tests,
    run_client_board_report,
)
from app.grc.models import (
    AiRiskAssessment,
    AiSystem,
    AiSystemClassification,
    Iso42001GapRecord,
    LifecycleStage,
    Nis2ObligationRecord,
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
from app.integrations.connectors import (
    clear_dispatch_log,
    get_dispatch_log,
    reset_connectors,
)
from app.integrations.datev_export import (
    clear_artifacts_for_tests,
    get_artifact,
    list_artifact_names,
)
from app.integrations.dispatcher import (
    DispatcherSettings,
    configure_dispatcher,
    dispatch_one,
    dispatch_pending,
)
from app.integrations.mandant_dossier import build_dossier
from app.integrations.models import (
    IntegrationJobStatus,
    IntegrationPayloadType,
    IntegrationTarget,
    JobWeight,
    classify_weight,
)
from app.integrations.outbox import enqueue_mandant_dossier
from app.integrations.sap_inbound import (
    process_sap_ai_system_event,
    validate_sap_envelope,
)
from app.integrations.store import (
    clear_for_tests as clear_integration,
)
from app.integrations.store import (
    configure_enabled_types,
    get_job,
    list_jobs,
    set_dossier_on_board_report,
)
from app.services.rag.evidence_store import (
    clear_for_tests as clear_events,
)
from app.services.rag.evidence_store import (
    list_all_events,
)


def _cleanup() -> None:
    clear_grc()
    clear_integration()
    clear_dispatch_log()
    clear_artifacts_for_tests()
    clear_events()
    reset_connectors()
    clear_reports_for_tests()
    clear_workflows_for_tests()
    configure_dispatcher(DispatcherSettings(enable_backoff=False))
    configure_enabled_types(set())


def _seed_mandant_data(
    tenant_id: str = "t1",
    client_id: str = "mandant-alpha",
) -> None:
    """Seed a realistic Mandant with AI systems and GRC records."""
    upsert_ai_system(
        AiSystem(
            tenant_id=tenant_id,
            client_id=client_id,
            system_id="chatbot-v1",
            name="Kundenservice-Chatbot",
            description="LLM-basierter Chatbot für Kundenanfragen",
            business_owner="Max Müller",
            ai_act_classification=AiSystemClassification.high_risk_candidate,
            lifecycle_stage=LifecycleStage.production,
            readiness_level=ReadinessLevel.partially_covered,
        )
    )
    upsert_ai_system(
        AiSystem(
            tenant_id=tenant_id,
            client_id=client_id,
            system_id="scoring-v2",
            name="Kredit-Scoring Engine",
            description="ML-basiertes Kreditscoring",
            business_owner="Lisa Schmidt",
            ai_act_classification=AiSystemClassification.high_risk,
            lifecycle_stage=LifecycleStage.testing,
            readiness_level=ReadinessLevel.insufficient_evidence,
            nis2_relevant=True,
            iso42001_in_scope=True,
        )
    )
    upsert_risk(
        AiRiskAssessment(
            tenant_id=tenant_id,
            client_id=client_id,
            system_id="chatbot-v1",
            risk_category="high",
            high_risk_likelihood="likely",
        )
    )
    upsert_risk(
        AiRiskAssessment(
            tenant_id=tenant_id,
            client_id=client_id,
            system_id="scoring-v2",
            risk_category="high",
            high_risk_likelihood="very_likely",
        )
    )
    upsert_nis2(
        Nis2ObligationRecord(
            tenant_id=tenant_id,
            client_id=client_id,
            system_id="scoring-v2",
            nis2_entity_type="essential",
            sector="finance",
        )
    )
    upsert_gap(
        Iso42001GapRecord(
            tenant_id=tenant_id,
            client_id=client_id,
            system_id="scoring-v2",
            control_families=["A.6_Planning", "A.7_Support"],
            gap_severity="major",
        )
    )
    upsert_gap(
        Iso42001GapRecord(
            tenant_id=tenant_id,
            client_id=client_id,
            system_id="chatbot-v1",
            control_families=["A.10_Performance"],
            gap_severity="minor",
        )
    )


# =========================================================================
# A) Mandanten-Dossier payload shape
# =========================================================================


class TestDossierPayloadShape:
    def test_dossier_basic_structure(self) -> None:
        _cleanup()
        _seed_mandant_data()
        d = build_dossier(
            tenant_id="t1",
            client_id="mandant-alpha",
            period="2026Q1",
            export_version=1,
            mandant_kurzname="Alpha GmbH",
            branche="Finanzdienstleistungen",
        )
        assert d["schema_version"] == "v1"
        assert d["export_type"] == "mandant_compliance_dossier"
        assert d["period"] == "2026Q1"
        assert d["export_version"] == 1
        assert d["exported_at"]

        stamm = d["stammdaten"]
        assert stamm["tenant_id"] == "t1"
        assert stamm["client_id"] == "mandant-alpha"
        assert stamm["mandant_kurzname"] == "Alpha GmbH"
        assert stamm["branche"] == "Finanzdienstleistungen"

    def test_dossier_ai_system_inventar(self) -> None:
        _cleanup()
        _seed_mandant_data()
        d = build_dossier(tenant_id="t1", client_id="mandant-alpha")
        systems = d["ai_system_inventar"]
        assert d["ai_systeme_gesamt"] == 2
        assert len(systems) == 2

        names = {s["name"] for s in systems}
        assert "Kundenservice-Chatbot" in names
        assert "Kredit-Scoring Engine" in names

        chatbot = next(s for s in systems if s["system_id"] == "chatbot-v1")
        assert chatbot["ki_act_klassifikation"] == "high_risk_candidate"
        assert chatbot["lebenszyklus_stufe"] == "production"
        assert chatbot["bereitschaftsgrad"] == "partially_covered"

        scoring = next(s for s in systems if s["system_id"] == "scoring-v2")
        assert scoring["nis2_relevant"] is True
        assert scoring["iso42001_im_scope"] is True

    def test_dossier_grc_sicht(self) -> None:
        _cleanup()
        _seed_mandant_data()
        d = build_dossier(tenant_id="t1", client_id="mandant-alpha")
        grc = d["grc_sicht"]

        assert grc["ai_risk_assessments"]["gesamt"] == 2
        assert grc["ai_risk_assessments"]["status_verteilung"]["open"] == 2

        assert grc["nis2_pflichten"]["gesamt"] == 1
        assert grc["nis2_pflichten"]["status_verteilung"]["identified"] == 1

        gaps = grc["iso42001_gaps"]
        assert gaps["gesamt"] == 2
        families = gaps["nach_control_family"]
        assert "A.6_Planning" in families
        assert "A.10_Performance" in families

    def test_dossier_empty_mandant(self) -> None:
        _cleanup()
        d = build_dossier(tenant_id="t1", client_id="empty-mandant")
        assert d["ai_systeme_gesamt"] == 0
        assert d["grc_sicht"]["ai_risk_assessments"]["gesamt"] == 0


# =========================================================================
# B) Period & versioning
# =========================================================================


class TestPeriodVersioning:
    def test_job_carries_period_and_version(self) -> None:
        _cleanup()
        configure_enabled_types({"mandant_compliance_dossier"})
        job = enqueue_mandant_dossier(
            tenant_id="t1",
            client_id="m1",
            period="2026Q1",
            export_version=2,
        )
        assert job is not None
        assert job.period == "2026Q1"
        assert job.export_version == 2
        assert job.schema_version == "v1"
        assert job.payload_type == IntegrationPayloadType.mandant_compliance_dossier

    def test_different_versions_are_separate_jobs(self) -> None:
        _cleanup()
        configure_enabled_types({"mandant_compliance_dossier"})
        j1 = enqueue_mandant_dossier(
            tenant_id="t1", client_id="m1", period="2026Q1", export_version=1
        )
        j2 = enqueue_mandant_dossier(
            tenant_id="t1", client_id="m1", period="2026Q1", export_version=2
        )
        assert j1 is not None and j2 is not None
        assert j1.job_id != j2.job_id

    def test_same_version_is_idempotent(self) -> None:
        _cleanup()
        configure_enabled_types({"mandant_compliance_dossier"})
        j1 = enqueue_mandant_dossier(
            tenant_id="t1", client_id="m1", period="2026Q1", export_version=1
        )
        j2 = enqueue_mandant_dossier(
            tenant_id="t1", client_id="m1", period="2026Q1", export_version=1
        )
        assert j1 is not None and j2 is not None
        assert j1.job_id == j2.job_id

    def test_dossier_classified_as_heavy(self) -> None:
        assert classify_weight(IntegrationPayloadType.mandant_compliance_dossier) == JobWeight.heavy


# =========================================================================
# C) Dispatcher integration (dossier build + DATEV connector)
# =========================================================================


class TestDossierDispatch:
    def test_dispatch_builds_dossier_and_stores_artifact(self) -> None:
        _cleanup()
        _seed_mandant_data()
        configure_enabled_types({"mandant_compliance_dossier"})

        job = enqueue_mandant_dossier(
            tenant_id="t1",
            client_id="mandant-alpha",
            period="2026Q1",
            export_version=1,
            mandant_kurzname="Alpha GmbH",
            branche="Finanzdienstleistungen",
        )
        assert job is not None
        ok = dispatch_one(job)
        assert ok is True

        refreshed = get_job(job.job_id, tenant_id="t1")
        assert refreshed is not None
        assert refreshed.status == IntegrationJobStatus.delivered
        assert refreshed.connector_artifact_name != ""

        artifact = get_artifact(refreshed.connector_artifact_name, tenant_id="t1")
        assert artifact is not None
        import json

        content = json.loads(artifact["content"])
        assert content["export_type"] == "mandant_compliance_dossier"
        assert content["period"] == "2026Q1"
        assert content["ai_systeme_gesamt"] == 2

    def test_dispatch_pending_includes_dossier(self) -> None:
        _cleanup()
        _seed_mandant_data()
        configure_enabled_types({"mandant_compliance_dossier"})

        enqueue_mandant_dossier(
            tenant_id="t1",
            client_id="mandant-alpha",
            period="2026Q1",
        )
        result = dispatch_pending()
        assert result["delivered"] >= 1

        artifacts = list_artifact_names(tenant_id="t1")
        assert len(artifacts) >= 1

    def test_dispatch_log_includes_dossier_metadata(self) -> None:
        _cleanup()
        _seed_mandant_data()
        configure_enabled_types({"mandant_compliance_dossier"})

        job = enqueue_mandant_dossier(
            tenant_id="t1",
            client_id="mandant-alpha",
            period="2026Q1",
        )
        assert job is not None
        dispatch_one(job)

        log = get_dispatch_log()
        dossier_entries = [e for e in log if e.get("payload_type") == "mandant_compliance_dossier"]
        assert len(dossier_entries) == 1
        assert dossier_entries[0]["period"] == "2026Q1"


# =========================================================================
# D) Evidence events for Kanzlei-Exports
# =========================================================================


class TestDossierEvidence:
    def test_dossier_dispatch_emits_evidence(self) -> None:
        _cleanup()
        _seed_mandant_data()
        configure_enabled_types({"mandant_compliance_dossier"})

        job = enqueue_mandant_dossier(
            tenant_id="t1",
            client_id="mandant-alpha",
            period="2026Q1",
            export_version=3,
        )
        assert job is not None
        dispatch_one(job)

        events = list_all_events()
        export_events = [e for e in events if e.get("event_type") == "mandant_compliance_export"]
        assert len(export_events) >= 1
        ev = export_events[0]
        assert ev["tenant_id"] == "t1"
        assert ev["client_id"] == "mandant-alpha"
        assert ev["period"] == "2026Q1"
        assert ev["export_version"] == 3
        assert ev["schema_version"] == "v1"


# =========================================================================
# E) Board-report → dossier auto-enqueue
# =========================================================================


class TestBoardReportDossierLinkage:
    def test_no_dossier_by_default(self) -> None:
        _cleanup()
        _seed_mandant_data()
        configure_enabled_types({"mandant_compliance_dossier"})

        run_client_board_report(
            tenant_id="t1",
            client_id="mandant-alpha",
            reporting_period="2026Q1",
        )
        jobs = list_jobs(tenant_id="t1", payload_type="mandant_compliance_dossier")
        assert len(jobs) == 0

    def test_dossier_enqueued_when_flag_enabled(self) -> None:
        _cleanup()
        _seed_mandant_data()
        configure_enabled_types({"mandant_compliance_dossier"})
        set_dossier_on_board_report(True)

        run_client_board_report(
            tenant_id="t1",
            client_id="mandant-alpha",
            reporting_period="2026Q1",
        )
        jobs = list_jobs(tenant_id="t1", payload_type="mandant_compliance_dossier")
        assert len(jobs) == 1
        assert jobs[0].period == "2026Q1"
        assert jobs[0].target == IntegrationTarget.datev_export


# =========================================================================
# F) SAP S/4 CloudEvents inbound endpoint
# =========================================================================


def _valid_sap_envelope(**overrides: object) -> dict:
    base: dict = {
        "specversion": "1.0",
        "type": "sap.s4.ai.system.created",
        "source": "sap.s4hana.finance.prod",
        "id": "evt-abc123",
        "time": "2026-03-31T10:00:00Z",
        "tenantid": "t1",
        "clientid": "mandant-alpha",
        "systemid": "chatbot-v1",
        "traceid": "trace-xyz",
        "data": {
            "system_id": "sap-scoring-01",
            "name": "SAP Kredit-Scoring",
            "description": "ML scoring from S/4",
            "business_owner": "Herr Finanz",
        },
    }
    base.update(overrides)
    return base


class TestSapInboundValidation:
    def test_valid_envelope_passes(self) -> None:
        errors = validate_sap_envelope(_valid_sap_envelope())
        assert errors == []

    def test_missing_specversion(self) -> None:
        env = _valid_sap_envelope()
        del env["specversion"]
        errors = validate_sap_envelope(env)
        assert any("specversion" in e for e in errors)

    def test_missing_type(self) -> None:
        env = _valid_sap_envelope()
        del env["type"]
        errors = validate_sap_envelope(env)
        assert any("type" in e for e in errors)

    def test_missing_tenantid(self) -> None:
        env = _valid_sap_envelope()
        del env["tenantid"]
        errors = validate_sap_envelope(env)
        assert any("tenantid" in e for e in errors)

    def test_missing_data(self) -> None:
        env = _valid_sap_envelope()
        del env["data"]
        errors = validate_sap_envelope(env)
        assert any("data" in e for e in errors)

    def test_missing_data_system_id(self) -> None:
        env = _valid_sap_envelope(data={"name": "test"})
        errors = validate_sap_envelope(env)
        assert any("system_id" in e for e in errors)

    def test_unsupported_specversion(self) -> None:
        env = _valid_sap_envelope(specversion="2.0")
        errors = validate_sap_envelope(env)
        assert any("specversion" in e for e in errors)

    def test_unrecognised_event_type(self) -> None:
        env = _valid_sap_envelope(type="sap.unknown.event")
        errors = validate_sap_envelope(env)
        assert any("event type" in e for e in errors)

    def test_invalid_data_type(self) -> None:
        env = _valid_sap_envelope(data="not-a-dict")
        errors = validate_sap_envelope(env)
        assert any("JSON object" in e for e in errors)


class TestSapInboundProcessing:
    def test_creates_ai_system_stub(self) -> None:
        _cleanup()
        result = process_sap_ai_system_event(_valid_sap_envelope())
        assert result["status"] == "accepted"
        assert result["system_id"] == "sap-scoring-01"
        assert result["tenant_id"] == "t1"

        ai_sys = get_ai_system(tenant_id="t1", system_id="sap-scoring-01")
        assert ai_sys is not None
        assert ai_sys.name == "SAP Kredit-Scoring"
        assert ai_sys.description == "ML scoring from S/4"
        assert ai_sys.business_owner == "Herr Finanz"

    def test_updates_existing_system_name(self) -> None:
        _cleanup()
        upsert_ai_system(
            AiSystem(
                tenant_id="t1",
                system_id="sap-scoring-01",
                name="",
            )
        )
        result = process_sap_ai_system_event(_valid_sap_envelope())
        assert result["status"] == "accepted"

        ai_sys = get_ai_system(tenant_id="t1", system_id="sap-scoring-01")
        assert ai_sys is not None
        assert ai_sys.name == "SAP Kredit-Scoring"

    def test_does_not_overwrite_existing_fields(self) -> None:
        _cleanup()
        upsert_ai_system(
            AiSystem(
                tenant_id="t1",
                system_id="sap-scoring-01",
                name="Existing Name",
                description="Existing Desc",
            )
        )
        result = process_sap_ai_system_event(_valid_sap_envelope())
        assert result["status"] == "accepted"

        ai_sys = get_ai_system(tenant_id="t1", system_id="sap-scoring-01")
        assert ai_sys is not None
        assert ai_sys.name == "Existing Name"
        assert ai_sys.description == "Existing Desc"

    def test_emits_evidence_event(self) -> None:
        _cleanup()
        process_sap_ai_system_event(_valid_sap_envelope())

        events = list_all_events()
        sap_events = [e for e in events if e.get("event_type") == "sap_btp_ai_system_event"]
        assert len(sap_events) >= 1
        ev = sap_events[0]
        assert ev["tenant_id"] == "t1"
        assert ev["system_id"] == "sap-scoring-01"
        assert ev["sap_event_type"] == "sap.s4.ai.system.created"
        assert ev["sap_source"] == "sap.s4hana.finance.prod"
        assert ev["envelope_id"] == "evt-abc123"
        assert ev["trace_id"] == "trace-xyz"

    def test_different_event_types_accepted(self) -> None:
        _cleanup()
        for etype in [
            "sap.s4.ai.system.created",
            "sap.s4.ai.system.updated",
            "sap.s4.ai.deployment.requested",
        ]:
            env = _valid_sap_envelope(type=etype, data={"system_id": f"sys-{etype}"})
            result = process_sap_ai_system_event(env)
            assert result["status"] == "accepted"


# =========================================================================
# G) Mandant-Export API trigger (integration-level, not HTTP)
# =========================================================================


class TestMandantExportTrigger:
    def test_enqueue_creates_datev_target_job(self) -> None:
        _cleanup()
        configure_enabled_types({"mandant_compliance_dossier"})
        job = enqueue_mandant_dossier(
            tenant_id="t1",
            client_id="m1",
            period="2026Q1",
        )
        assert job is not None
        assert job.target == IntegrationTarget.datev_export
        assert job.payload_type == IntegrationPayloadType.mandant_compliance_dossier

    def test_enqueue_blocked_if_type_not_enabled(self) -> None:
        _cleanup()
        configure_enabled_types({"ai_risk_assessment"})
        job = enqueue_mandant_dossier(
            tenant_id="t1",
            client_id="m1",
            period="2026Q1",
        )
        assert job is None
