"""Tests for Wave 15 — Enterprise integration outbox, connectors, dispatcher.

Covers:
- IntegrationJob model + enums
- Outbox creation & idempotency
- Feature-flag filtering (ENABLED_PAYLOAD_TYPES)
- Payload mapping for each source entity type (DATEV + SAP)
- Job lifecycle transitions (pending → delivered, failed → retry)
- Dead-letter handling after MAX_DISPATCH_ATTEMPTS failures
- Dispatcher end-to-end with stub connectors
- Tenant/client/system propagation through evidence logs
- Connector dispatch log correctness
"""

from __future__ import annotations

from app.grc.client_board_report_service import (
    ClientBoardReport,
    _store_report,
    clear_reports_for_tests,
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
    upsert_ai_system,
    upsert_gap,
    upsert_nis2,
    upsert_risk,
)
from app.integrations.connectors import (
    FailingConnector,
    clear_dispatch_log,
    get_dispatch_log,
    register_connector,
    reset_connectors,
)
from app.integrations.dispatcher import dispatch_one, dispatch_pending
from app.integrations.mappers import (
    map_gap_datev,
    map_gap_sap,
    map_nis2_datev,
    map_nis2_sap,
    map_readiness_datev,
    map_readiness_sap,
    map_risk_datev,
    map_risk_sap,
    resolve_mapper,
)
from app.integrations.models import (
    MAX_DISPATCH_ATTEMPTS,
    IntegrationJob,
    IntegrationJobStatus,
    IntegrationPayloadType,
    IntegrationTarget,
)
from app.integrations.outbox import enqueue_for_entity
from app.integrations.store import (
    clear_for_tests as clear_integration,
)
from app.integrations.store import (
    configure_enabled_types,
    enqueue_job,
    get_job,
    list_jobs,
    mark_for_retry,
    update_job_status,
)
from app.services.rag.evidence_store import (
    clear_for_tests as clear_evidence,
)
from app.services.rag.evidence_store import (
    list_all_events,
)


def _cleanup() -> None:
    clear_evidence()
    clear_grc()
    clear_integration()
    clear_dispatch_log()
    reset_connectors()
    clear_reports_for_tests()


# ── Model & enums ────────────────────────────────────────────────────


class TestModelBasics:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_job_defaults(self) -> None:
        job = IntegrationJob(tenant_id="t1")
        assert job.job_id.startswith("INTJOB-")
        assert job.status == IntegrationJobStatus.pending
        assert job.attempt_count == 0

    def test_enums_complete(self) -> None:
        assert set(IntegrationTarget) == {
            IntegrationTarget.datev_export,
            IntegrationTarget.sap_btp,
            IntegrationTarget.generic_partner_api,
        }
        assert IntegrationJobStatus.dead_letter in IntegrationJobStatus
        assert IntegrationPayloadType.board_report_summary in IntegrationPayloadType


# ── Outbox creation & idempotency ────────────────────────────────────


class TestOutboxCreation:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_enqueue_creates_job(self) -> None:
        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-001",
            tenant_id="t1",
            client_id="c1",
            system_id="sys-1",
            target=IntegrationTarget.datev_export,
        )
        assert job is not None
        assert job.payload_type == IntegrationPayloadType.ai_risk_assessment
        assert job.tenant_id == "t1"
        assert job.client_id == "c1"

    def test_idempotency_returns_existing(self) -> None:
        job1 = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-001",
            tenant_id="t1",
            target=IntegrationTarget.datev_export,
        )
        job2 = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-001",
            tenant_id="t1",
            target=IntegrationTarget.datev_export,
        )
        assert job1 is not None
        assert job2 is not None
        assert job1.job_id == job2.job_id

    def test_different_targets_create_separate_jobs(self) -> None:
        j1 = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-001",
            tenant_id="t1",
            target=IntegrationTarget.datev_export,
        )
        j2 = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-001",
            tenant_id="t1",
            target=IntegrationTarget.sap_btp,
        )
        assert j1 is not None and j2 is not None
        assert j1.job_id != j2.job_id

    def test_unknown_entity_type_returns_none(self) -> None:
        job = enqueue_for_entity(
            entity_type="SomethingWeird",
            entity_id="X-1",
            tenant_id="t1",
        )
        assert job is None

    def test_feature_flag_blocks_disabled_types(self) -> None:
        configure_enabled_types({"nis2_obligation"})
        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-002",
            tenant_id="t1",
        )
        assert job is None

    def test_feature_flag_allows_enabled_types(self) -> None:
        configure_enabled_types({"ai_risk_assessment"})
        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-003",
            tenant_id="t1",
        )
        assert job is not None


# ── Payload mapping ──────────────────────────────────────────────────


class TestPayloadMapping:
    def test_risk_datev(self) -> None:
        rec = AiRiskAssessment(
            id="RISK-M1",
            tenant_id="t1",
            client_id="c1",
            system_id="sys-1",
            risk_category="high",
            use_case_type="credit_scoring",
        )
        p = map_risk_datev(rec)
        assert p["schema_version"] == "v1"
        assert p["record_type"] == "Risikobewertung_KI"
        assert p["risikokategorie"] == "high"
        assert p["tenant_id"] == "t1"

    def test_risk_sap(self) -> None:
        rec = AiRiskAssessment(
            id="RISK-M2",
            tenant_id="t1",
            risk_category="limited",
        )
        p = map_risk_sap(rec)
        assert p["record_type"] == "ai_risk_assessment"
        assert p["risk_category"] == "limited"

    def test_nis2_datev(self) -> None:
        rec = Nis2ObligationRecord(
            id="NIS2-M1",
            tenant_id="t1",
            sector="energy",
            obligation_tags=["incident_reporting"],
        )
        p = map_nis2_datev(rec)
        assert p["record_type"] == "NIS2_Pflicht"
        assert p["sektor"] == "energy"
        assert "incident_reporting" in p["pflicht_tags"]

    def test_nis2_sap(self) -> None:
        rec = Nis2ObligationRecord(id="NIS2-M2", tenant_id="t1")
        p = map_nis2_sap(rec)
        assert p["record_type"] == "nis2_obligation"

    def test_gap_datev(self) -> None:
        rec = Iso42001GapRecord(
            id="GAP-M1",
            tenant_id="t1",
            control_families=["A.6"],
            gap_severity="major",
        )
        p = map_gap_datev(rec)
        assert p["record_type"] == "ISO42001_Luecke"
        assert p["schweregrad"] == "major"
        assert "A.6" in p["kontroll_familien"]

    def test_gap_sap(self) -> None:
        rec = Iso42001GapRecord(id="GAP-M2", tenant_id="t1")
        p = map_gap_sap(rec)
        assert p["record_type"] == "iso42001_gap"

    def test_readiness_datev(self) -> None:
        sys = AiSystem(
            id="SYS-M1",
            system_id="sys-1",
            tenant_id="t1",
            lifecycle_stage=LifecycleStage.production,
            readiness_level=ReadinessLevel.ready_for_review,
            ai_act_classification=AiSystemClassification.high_risk_candidate,
        )
        p = map_readiness_datev(sys)
        assert p["record_type"] == "KI_System_Bereitschaft"
        assert p["lebenszyklus_stufe"] == "production"
        assert p["ki_act_klassifikation"] == "high_risk_candidate"

    def test_readiness_sap(self) -> None:
        sys = AiSystem(
            id="SYS-M2",
            system_id="sys-2",
            tenant_id="t1",
        )
        p = map_readiness_sap(sys)
        assert p["record_type"] == "ai_system_readiness_snapshot"

    def test_resolve_mapper_all_combinations(self) -> None:
        for pt in IntegrationPayloadType:
            for tgt in IntegrationTarget:
                mapper = resolve_mapper(pt.value, tgt.value)
                assert mapper is not None, f"No mapper for ({pt.value}, {tgt.value})"


# ── Job lifecycle ────────────────────────────────────────────────────


class TestJobLifecycle:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_pending_to_delivered(self) -> None:
        job = IntegrationJob(
            tenant_id="t1",
            target=IntegrationTarget.datev_export,
            payload_type=IntegrationPayloadType.ai_risk_assessment,
        )
        enqueue_job(job)

        updated = update_job_status(job.job_id, IntegrationJobStatus.dispatched)
        assert updated is not None
        assert updated.status == IntegrationJobStatus.dispatched
        assert updated.attempt_count == 1

        delivered = update_job_status(job.job_id, IntegrationJobStatus.delivered)
        assert delivered is not None
        assert delivered.status == IntegrationJobStatus.delivered

    def test_failed_to_retry(self) -> None:
        job = IntegrationJob(tenant_id="t1")
        enqueue_job(job)
        update_job_status(job.job_id, IntegrationJobStatus.failed)

        retried = mark_for_retry(job.job_id)
        assert retried is not None
        assert retried.status == IntegrationJobStatus.pending

    def test_retry_only_allowed_for_failed_or_deadletter(self) -> None:
        job = IntegrationJob(tenant_id="t1")
        enqueue_job(job)

        retried = mark_for_retry(job.job_id)
        assert retried is None

    def test_list_jobs_filters(self) -> None:
        j1 = IntegrationJob(
            tenant_id="t1",
            target=IntegrationTarget.datev_export,
            payload_type=IntegrationPayloadType.ai_risk_assessment,
        )
        j2 = IntegrationJob(
            tenant_id="t2",
            target=IntegrationTarget.sap_btp,
            payload_type=IntegrationPayloadType.nis2_obligation,
        )
        enqueue_job(j1)
        enqueue_job(j2)

        assert len(list_jobs(tenant_id="t1")) == 1
        assert len(list_jobs(target="sap_btp")) == 1
        assert len(list_jobs(payload_type="nis2_obligation")) == 1
        assert len(list_jobs()) == 2


# ── Dead-letter ──────────────────────────────────────────────────────


class TestDeadLetter:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_dead_letter_after_max_attempts(self) -> None:
        register_connector("datev_export", FailingConnector())

        risk = AiRiskAssessment(
            id="RISK-DL",
            tenant_id="t1",
            client_id="c1",
            system_id="sys-1",
            risk_category="high",
        )
        upsert_risk(risk)

        job = IntegrationJob(
            tenant_id="t1",
            target=IntegrationTarget.datev_export,
            payload_type=IntegrationPayloadType.ai_risk_assessment,
            source_entity_type="AiRiskAssessment",
            source_entity_id="RISK-DL",
        )
        enqueue_job(job)

        for i in range(MAX_DISPATCH_ATTEMPTS):
            if job.status != IntegrationJobStatus.pending:
                mark_for_retry(job.job_id)
            dispatch_one(job)

        refreshed = get_job(job.job_id)
        assert refreshed is not None
        assert refreshed.status == IntegrationJobStatus.dead_letter
        assert refreshed.attempt_count >= MAX_DISPATCH_ATTEMPTS

    def test_dead_letter_can_be_retried(self) -> None:
        job = IntegrationJob(tenant_id="t1")
        enqueue_job(job)
        update_job_status(job.job_id, IntegrationJobStatus.dead_letter)

        retried = mark_for_retry(job.job_id)
        assert retried is not None
        assert retried.status == IntegrationJobStatus.pending


# ── Dispatcher end-to-end ────────────────────────────────────────────


class TestDispatcherE2E:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_dispatch_risk_to_datev(self) -> None:
        risk = AiRiskAssessment(
            id="RISK-D1",
            tenant_id="t1",
            client_id="c1",
            system_id="sys-1",
            risk_category="high",
        )
        upsert_risk(risk)

        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-D1",
            tenant_id="t1",
            client_id="c1",
            system_id="sys-1",
            target=IntegrationTarget.datev_export,
        )
        assert job is not None

        ok = dispatch_one(job)
        assert ok is True

        refreshed = get_job(job.job_id)
        assert refreshed is not None
        assert refreshed.status == IntegrationJobStatus.delivered

        log = get_dispatch_log()
        assert len(log) == 1
        assert log[0]["connector"] == "datev_export"
        assert log[0]["payload"]["risikokategorie"] == "high"

    def test_dispatch_nis2_to_sap(self) -> None:
        nis2 = Nis2ObligationRecord(
            id="NIS2-D1",
            tenant_id="t1",
            sector="energy",
        )
        upsert_nis2(nis2)

        job = enqueue_for_entity(
            entity_type="Nis2ObligationRecord",
            entity_id="NIS2-D1",
            tenant_id="t1",
            target=IntegrationTarget.sap_btp,
        )
        assert job is not None
        ok = dispatch_one(job)
        assert ok is True

        log = get_dispatch_log()
        assert len(log) == 1
        assert log[0]["connector"] == "sap_btp"

    def test_dispatch_gap_to_generic(self) -> None:
        gap = Iso42001GapRecord(
            id="GAP-D1",
            tenant_id="t1",
            gap_severity="major",
        )
        upsert_gap(gap)

        job = enqueue_for_entity(
            entity_type="Iso42001GapRecord",
            entity_id="GAP-D1",
            tenant_id="t1",
            target=IntegrationTarget.generic_partner_api,
        )
        assert job is not None
        ok = dispatch_one(job)
        assert ok is True

    def test_dispatch_readiness_snapshot(self) -> None:
        sys = AiSystem(
            id="SYS-D1",
            system_id="sys-d1",
            tenant_id="t1",
            lifecycle_stage=LifecycleStage.production,
        )
        upsert_ai_system(sys)

        job = enqueue_for_entity(
            entity_type="AiSystemReadinessSnapshot",
            entity_id="SYS-D1",
            tenant_id="t1",
            system_id="sys-d1",
            target=IntegrationTarget.sap_btp,
        )
        assert job is not None
        ok = dispatch_one(job)
        assert ok is True

    def test_dispatch_board_report(self) -> None:
        report = ClientBoardReport(
            id="CBR-D1",
            tenant_id="t1",
            client_id="c1",
            reporting_period="2025-Q4",
            systems_included=3,
            highlights=["All systems operational"],
        )
        _store_report(report)

        job = enqueue_for_entity(
            entity_type="ClientBoardReport",
            entity_id="CBR-D1",
            tenant_id="t1",
            client_id="c1",
            target=IntegrationTarget.datev_export,
        )
        assert job is not None
        ok = dispatch_one(job)
        assert ok is True

        log = get_dispatch_log()
        assert len(log) == 1
        assert log[0]["payload"]["record_type"] == "Mandanten_Board_Bericht"

    def test_dispatch_pending_processes_all(self) -> None:
        r1 = AiRiskAssessment(id="RISK-P1", tenant_id="t1", system_id="s1")
        r2 = AiRiskAssessment(id="RISK-P2", tenant_id="t1", system_id="s2")
        upsert_risk(r1)
        upsert_risk(r2)

        enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-P1",
            tenant_id="t1",
            system_id="s1",
            target=IntegrationTarget.datev_export,
        )
        enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-P2",
            tenant_id="t1",
            system_id="s2",
            target=IntegrationTarget.sap_btp,
        )

        counts = dispatch_pending()
        assert counts["delivered"] == 2
        assert counts["failed"] == 0


# ── Evidence / audit trail ───────────────────────────────────────────


class TestEvidenceTrail:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_creation_emits_evidence(self) -> None:
        enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-EV1",
            tenant_id="t-ev",
            client_id="c-ev",
            system_id="sys-ev",
            target=IntegrationTarget.datev_export,
            trace_id="trace-001",
        )
        events = list_all_events()
        created = [e for e in events if e.get("event_type") == "integration_job_created"]
        assert len(created) == 1
        ev = created[0]
        assert ev["tenant_id"] == "t-ev"
        assert ev["client_id"] == "c-ev"
        assert ev["system_id"] == "sys-ev"
        assert ev["target"] == "datev_export"
        assert ev["trace_id"] == "trace-001"

    def test_delivery_emits_evidence(self) -> None:
        risk = AiRiskAssessment(id="RISK-EV2", tenant_id="t-ev")
        upsert_risk(risk)

        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-EV2",
            tenant_id="t-ev",
            target=IntegrationTarget.datev_export,
        )
        assert job is not None
        dispatch_one(job)

        events = list_all_events()
        delivered = [e for e in events if e.get("event_type") == "integration_job_delivered"]
        assert len(delivered) == 1

    def test_failure_emits_evidence(self) -> None:
        register_connector("datev_export", FailingConnector())
        risk = AiRiskAssessment(id="RISK-EV3", tenant_id="t-ev")
        upsert_risk(risk)

        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-EV3",
            tenant_id="t-ev",
            target=IntegrationTarget.datev_export,
        )
        assert job is not None
        dispatch_one(job)

        events = list_all_events()
        failed = [e for e in events if e.get("event_type") == "integration_job_failed"]
        assert len(failed) >= 1

    def test_retry_emits_evidence(self) -> None:
        job = IntegrationJob(tenant_id="t-ev")
        enqueue_job(job)
        update_job_status(job.job_id, IntegrationJobStatus.failed)
        mark_for_retry(job.job_id)

        events = list_all_events()
        retried = [e for e in events if e.get("event_type") == "integration_job_retried"]
        assert len(retried) == 1
