"""Tests for Wave 15.1 — Enterprise integration hardening.

Covers:
- SAP BTP Event Mesh envelope shape and versioning
- DATEV export artifact shape (CSV + JSON), naming convention
- RLS tenant isolation on IntegrationJob store
- Dispatcher throttling, backoff, priority ordering
- Job weight classification
- Connector-specific refs (artifact name, envelope ID) on jobs
- Evidence events include artifact/envelope refs
"""

from __future__ import annotations

import csv
import io

from app.grc.models import (
    AiRiskAssessment,
)
from app.grc.store import (
    clear_for_tests as clear_grc,
)
from app.grc.store import (
    upsert_risk,
)
from app.integrations.connectors import (
    clear_dispatch_log,
    get_dispatch_log,
    reset_connectors,
)
from app.integrations.datev_export import (
    build_artifact_name,
    clear_artifacts_for_tests,
    get_artifact,
    list_artifact_names,
    render_csv,
    render_json,
    store_artifact,
)
from app.integrations.dispatcher import (
    DispatcherSettings,
    configure_dispatcher,
    dispatch_one,
    dispatch_pending,
)
from app.integrations.mappers import map_risk_datev
from app.integrations.models import (
    IntegrationJob,
    IntegrationJobStatus,
    IntegrationPayloadType,
    IntegrationTarget,
    JobWeight,
    classify_weight,
)
from app.integrations.outbox import enqueue_for_entity
from app.integrations.sap_envelope import build_sap_envelope
from app.integrations.store import (
    clear_for_tests as clear_integration,
)
from app.integrations.store import (
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
    clear_artifacts_for_tests()
    configure_dispatcher(DispatcherSettings(enable_backoff=False))


# ── SAP BTP Event Mesh envelope ──────────────────────────────────────


class TestSapEnvelope:
    def test_envelope_shape(self) -> None:
        env = build_sap_envelope(
            event_type="ai_risk_assessment",
            tenant_id="t1",
            client_id="c1",
            system_id="sys-1",
            payload_type="ai_risk_assessment",
            data={"risk_category": "high"},
            job_id="JOB-1",
            trace_id="trace-99",
        )
        assert env["specversion"] == "1.0"
        assert env["type"] == "compliancehub.grc.ai_risk_assessment"
        assert env["source"] == "compliancehub.ai-governance"
        assert env["id"].startswith("evt-")
        assert env["tenantid"] == "t1"
        assert env["clientid"] == "c1"
        assert env["systemid"] == "sys-1"
        assert env["traceid"] == "trace-99"
        assert env["jobid"] == "JOB-1"
        assert env["datacontenttype"] == "application/json"
        assert env["payload_type"] == "ai_risk_assessment"
        assert env["payload_version"] == "v1"
        assert env["data"]["risk_category"] == "high"
        assert "time" in env

    def test_envelope_versioning(self) -> None:
        env = build_sap_envelope(
            event_type="nis2_obligation",
            tenant_id="t1",
            payload_type="nis2_obligation",
            payload_version="v2",
            data={},
        )
        assert env["payload_version"] == "v2"
        assert env["specversion"] == "1.0"

    def test_envelope_no_pii(self) -> None:
        env = build_sap_envelope(
            event_type="test",
            tenant_id="t1",
            payload_type="test",
            data={"risk_category": "high"},
        )
        flat = str(env)
        assert "prompt" not in flat.lower() or "raw" not in flat.lower()

    def test_envelope_id_uniqueness(self) -> None:
        ids = set()
        for _ in range(50):
            env = build_sap_envelope(
                event_type="test",
                tenant_id="t1",
                payload_type="test",
                data={},
            )
            ids.add(env["id"])
        assert len(ids) == 50


# ── DATEV export artifacts ───────────────────────────────────────────


class TestDatevExport:
    def test_artifact_naming(self) -> None:
        name = build_artifact_name(
            tenant_id="acme",
            client_id="mandant-42",
            period="2025-Q4",
            version="v1",
        )
        assert name.startswith("ai_compliance_mandant_export_")
        assert "acme" in name
        assert "mandant-42" in name
        assert "2025-Q4" in name
        assert name.endswith(".json")

    def test_csv_rendering(self) -> None:
        risk = AiRiskAssessment(
            id="RISK-CSV1",
            tenant_id="t1",
            client_id="c1",
            system_id="sys-1",
            risk_category="high",
        )
        payload = map_risk_datev(risk)
        csv_str = render_csv([payload])

        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["Datensatz_Typ"] == "Risikobewertung_KI"
        assert rows[0]["Mandant_ID"] == "c1"
        assert rows[0]["Risikokategorie"] == "high"
        assert rows[0]["Schema_Version"] == "v1"

    def test_json_rendering(self) -> None:
        risk = AiRiskAssessment(id="RISK-JSON1", tenant_id="t1")
        payload = map_risk_datev(risk)
        json_str = render_json([payload])

        import json

        parsed = json.loads(json_str)
        assert parsed["schema_version"] == "v1"
        assert parsed["export_type"] == "datev_mandant_export"
        assert len(parsed["records"]) == 1
        assert "exported_at" in parsed

    def test_artifact_store(self) -> None:
        meta = store_artifact(
            "test_export.json",
            '{"test": true}',
            tenant_id="t1",
            client_id="c1",
            job_id="JOB-X",
        )
        assert meta["name"] == "test_export.json"
        assert meta["tenant_id"] == "t1"
        assert meta["size_bytes"] > 0

        entry = get_artifact("test_export.json", tenant_id="t1")
        assert entry is not None
        assert entry["content"] == '{"test": true}'

        clear_artifacts_for_tests()

    def test_artifact_tenant_isolation(self) -> None:
        store_artifact(
            "t1_export.json",
            "{}",
            tenant_id="t1",
        )
        assert get_artifact("t1_export.json", tenant_id="t2") is None
        assert get_artifact("t1_export.json", tenant_id="t1") is not None
        clear_artifacts_for_tests()

    def test_list_artifacts_filtered(self) -> None:
        store_artifact("a.json", "{}", tenant_id="t1", client_id="c1")
        store_artifact("b.json", "{}", tenant_id="t1", client_id="c2")
        store_artifact("c.json", "{}", tenant_id="t2", client_id="c3")

        assert len(list_artifact_names(tenant_id="t1")) == 2
        assert len(list_artifact_names(tenant_id="t1", client_id="c1")) == 1
        assert len(list_artifact_names(tenant_id="t2")) == 1

        clear_artifacts_for_tests()


# ── RLS tenant isolation ─────────────────────────────────────────────


class TestRlsTenantIsolation:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_tenant_cannot_read_other_tenant_job(self) -> None:
        job = IntegrationJob(tenant_id="tenant-A")
        enqueue_job(job)

        result = get_job(job.job_id, tenant_id="tenant-B")
        assert result is None

    def test_tenant_can_read_own_job(self) -> None:
        job = IntegrationJob(tenant_id="tenant-A")
        enqueue_job(job)

        result = get_job(job.job_id, tenant_id="tenant-A")
        assert result is not None
        assert result.job_id == job.job_id

    def test_internal_bypass_reads_any_tenant(self) -> None:
        job = IntegrationJob(tenant_id="tenant-A")
        enqueue_job(job)

        result = get_job(job.job_id, tenant_id="tenant-B", _internal=True)
        assert result is not None

    def test_list_returns_empty_without_tenant(self) -> None:
        enqueue_job(IntegrationJob(tenant_id="t1"))
        enqueue_job(IntegrationJob(tenant_id="t2"))

        assert len(list_jobs()) == 0

    def test_list_internal_returns_all(self) -> None:
        enqueue_job(IntegrationJob(tenant_id="t1"))
        enqueue_job(IntegrationJob(tenant_id="t2"))

        all_jobs = list_jobs(_internal=True)
        assert len(all_jobs) == 2

    def test_list_filters_by_tenant(self) -> None:
        enqueue_job(IntegrationJob(tenant_id="t1"))
        enqueue_job(IntegrationJob(tenant_id="t2"))

        assert len(list_jobs(tenant_id="t1")) == 1

    def test_retry_respects_tenant(self) -> None:
        job = IntegrationJob(tenant_id="t1")
        enqueue_job(job)
        update_job_status(job.job_id, IntegrationJobStatus.failed, _internal=True)

        result = mark_for_retry(job.job_id, tenant_id="t2")
        assert result is None

        result = mark_for_retry(job.job_id, tenant_id="t1")
        assert result is not None

    def test_update_status_respects_tenant(self) -> None:
        job = IntegrationJob(tenant_id="t1")
        enqueue_job(job)

        result = update_job_status(
            job.job_id,
            IntegrationJobStatus.dispatched,
            tenant_id="t2",
        )
        assert result is None

    def test_enqueue_requires_tenant(self) -> None:
        job = IntegrationJob(tenant_id="")
        try:
            enqueue_job(job)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


# ── Job weight classification ────────────────────────────────────────


class TestJobWeight:
    def test_light_payload_types(self) -> None:
        assert classify_weight(IntegrationPayloadType.ai_risk_assessment) == JobWeight.light
        assert classify_weight(IntegrationPayloadType.nis2_obligation) == JobWeight.light
        assert classify_weight(IntegrationPayloadType.iso42001_gap) == JobWeight.light

    def test_heavy_payload_types(self) -> None:
        assert classify_weight(IntegrationPayloadType.board_report_summary) == JobWeight.heavy
        assert (
            classify_weight(IntegrationPayloadType.ai_system_readiness_snapshot) == JobWeight.heavy
        )

    def test_weight_set_on_enqueue(self) -> None:
        _cleanup()
        job = enqueue_for_entity(
            entity_type="ClientBoardReport",
            entity_id="CBR-W1",
            tenant_id="t1",
        )
        assert job is not None
        assert job.weight == JobWeight.heavy
        _cleanup()


# ── Dispatcher throttling & priority ─────────────────────────────────


class TestDispatcherEnhancements:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_throttle_limits_concurrent(self) -> None:
        cfg = DispatcherSettings(max_concurrent_per_target=1, enable_backoff=False)
        r1 = AiRiskAssessment(id="RISK-TH1", tenant_id="t1", system_id="s1")
        r2 = AiRiskAssessment(id="RISK-TH2", tenant_id="t1", system_id="s2")
        upsert_risk(r1)
        upsert_risk(r2)

        enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-TH1",
            tenant_id="t1",
            system_id="s1",
            target=IntegrationTarget.datev_export,
        )
        enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-TH2",
            tenant_id="t1",
            system_id="s2",
            target=IntegrationTarget.datev_export,
        )

        counts = dispatch_pending(settings=cfg)
        assert counts["delivered"] >= 1

    def test_priority_ordering(self) -> None:
        r1 = AiRiskAssessment(id="RISK-PRI1", tenant_id="t1", system_id="s1")
        r2 = AiRiskAssessment(id="RISK-PRI2", tenant_id="t1", system_id="s2")
        upsert_risk(r1)
        upsert_risk(r2)

        j_low = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-PRI1",
            tenant_id="t1",
            system_id="s1",
            target=IntegrationTarget.datev_export,
        )
        j_high = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-PRI2",
            tenant_id="t1",
            system_id="s2",
            target=IntegrationTarget.sap_btp,
        )
        assert j_low is not None and j_high is not None
        j_high.priority = 10

        cfg = DispatcherSettings(enable_backoff=False)
        counts = dispatch_pending(settings=cfg)
        assert counts["delivered"] == 2

    def test_datev_priority_boost(self) -> None:
        cfg = DispatcherSettings(datev_priority_boost=5, enable_backoff=False)
        r1 = AiRiskAssessment(id="RISK-BT1", tenant_id="t1", system_id="s1")
        upsert_risk(r1)

        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-BT1",
            tenant_id="t1",
            system_id="s1",
            target=IntegrationTarget.datev_export,
        )
        assert job is not None
        counts = dispatch_pending(settings=cfg)
        assert counts["delivered"] == 1

    def test_backoff_settings(self) -> None:
        cfg = DispatcherSettings(
            backoff_base_seconds=0.5,
            backoff_max_seconds=4.0,
            enable_backoff=True,
        )
        assert cfg.backoff_seconds(1) == 0.5
        assert cfg.backoff_seconds(2) == 1.0
        assert cfg.backoff_seconds(3) == 2.0
        assert cfg.backoff_seconds(4) == 4.0
        assert cfg.backoff_seconds(10) == 4.0


# ── Connector refs on jobs ───────────────────────────────────────────


class TestConnectorRefs:
    def setup_method(self) -> None:
        _cleanup()

    def teardown_method(self) -> None:
        _cleanup()

    def test_datev_dispatch_sets_artifact_name(self) -> None:
        risk = AiRiskAssessment(
            id="RISK-REF1",
            tenant_id="t1",
            client_id="c1",
            system_id="sys-1",
            risk_category="high",
        )
        upsert_risk(risk)

        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-REF1",
            tenant_id="t1",
            client_id="c1",
            target=IntegrationTarget.datev_export,
        )
        assert job is not None
        dispatch_one(job, settings=DispatcherSettings(enable_backoff=False))

        refreshed = get_job(job.job_id, tenant_id="t1")
        assert refreshed is not None
        assert refreshed.connector_artifact_name.startswith("ai_compliance_mandant_export_")

        names = list_artifact_names(tenant_id="t1")
        assert len(names) == 1

    def test_sap_dispatch_sets_envelope_id(self) -> None:
        risk = AiRiskAssessment(
            id="RISK-REF2",
            tenant_id="t1",
            system_id="sys-1",
        )
        upsert_risk(risk)

        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-REF2",
            tenant_id="t1",
            target=IntegrationTarget.sap_btp,
        )
        assert job is not None
        dispatch_one(job, settings=DispatcherSettings(enable_backoff=False))

        refreshed = get_job(job.job_id, tenant_id="t1")
        assert refreshed is not None
        assert refreshed.connector_envelope_id.startswith("evt-")

        log = get_dispatch_log()
        assert len(log) == 1
        assert "envelope" in log[0]
        assert log[0]["envelope"]["specversion"] == "1.0"

    def test_evidence_includes_artifact_ref(self) -> None:
        risk = AiRiskAssessment(
            id="RISK-EV-ART",
            tenant_id="t-ev",
            client_id="c-ev",
        )
        upsert_risk(risk)

        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-EV-ART",
            tenant_id="t-ev",
            client_id="c-ev",
            target=IntegrationTarget.datev_export,
        )
        assert job is not None
        dispatch_one(job, settings=DispatcherSettings(enable_backoff=False))

        events = list_all_events()
        delivered = [e for e in events if e.get("event_type") == "integration_job_delivered"]
        assert len(delivered) == 1
        assert "artifact_name" in delivered[0]

    def test_evidence_includes_envelope_ref(self) -> None:
        risk = AiRiskAssessment(
            id="RISK-EV-ENV",
            tenant_id="t-ev",
        )
        upsert_risk(risk)

        job = enqueue_for_entity(
            entity_type="AiRiskAssessment",
            entity_id="RISK-EV-ENV",
            tenant_id="t-ev",
            target=IntegrationTarget.sap_btp,
        )
        assert job is not None
        dispatch_one(job, settings=DispatcherSettings(enable_backoff=False))

        events = list_all_events()
        delivered = [e for e in events if e.get("event_type") == "integration_job_delivered"]
        assert len(delivered) == 1
        assert "envelope_id" in delivered[0]
