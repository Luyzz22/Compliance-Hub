"""Wave 4: OpenTelemetry spans align with RAG logs; Temporal activity carrier stitching."""

from __future__ import annotations

import json
import logging
import uuid
from unittest.mock import patch

import pytest
from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore
from opentelemetry import trace

from app.policy.opa_client import PolicyDecision
from app.rag.models import EuRegRagLlmCitation, EuRegRagLlmOutput
from app.rag.store import (
    replace_eu_reg_document_store_for_tests,
    reset_eu_reg_document_store_for_tests,
)
from app.telemetry.tracing import configure_telemetry_test_memory_exporter, inject_trace_carrier
from app.workflows.board_report import BoardReportWorkflowInput
from app.workflows.board_report_activities import load_tenant_board_snapshot_activity


@pytest.fixture
def otel_exporter() -> object:
    exporter = configure_telemetry_test_memory_exporter()
    yield exporter
    exporter.clear()


def _minimal_rag_store() -> InMemoryDocumentStore:
    store = InMemoryDocumentStore()
    store.write_documents(
        [
            Document(
                id="eu-ai-act-art9-chunk-0",
                content=(
                    "Anbieter von Hochrisiko-KI-Systemen müssen ein Risikomanagementsystem "
                    "einrichten und dokumentieren."
                ),
                meta={
                    "source": "EU AI Act (Pilot)",
                    "section": "Art. 9 Risikomanagement",
                    "rag_scope": "global",
                },
            ),
        ],
    )
    return store


def _rag_headers() -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-advisor-id": "advisor-otel-test",
    }


def test_rag_http_spans_and_log_share_trace_id(
    otel_exporter: object,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_COMPLIANCE_RAG_KNOWLEDGE_HUB", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_BM25_MIN_SCORE", "0.01")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_CONFIDENCE_HIGH_MIN_SCORE", "0.01")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_CONFIDENCE_GAP_MIN", "0.0")

    store = _minimal_rag_store()
    tid = f"otel-rag-{uuid.uuid4().hex[:8]}"
    replace_eu_reg_document_store_for_tests(store)
    fixed = EuRegRagLlmOutput(
        answer_de="Antwort mit Spur.",
        citations=[
            EuRegRagLlmCitation(
                doc_id="eu-ai-act-art9-chunk-0",
                source="EU AI Act (Pilot)",
                section="Art. 9",
            ),
        ],
    )
    caplog.set_level(logging.INFO)

    try:
        with (
            patch(
                "app.policy.policy_guard.evaluate_action_policy",
                return_value=PolicyDecision(allowed=True, reason="ok"),
            ),
            patch(
                "app.rag.pipelines.eu_ai_act_nis2_pipeline.generate_eu_reg_rag_llm_output",
                return_value=fixed,
            ),
            TestClient(app) as client,
        ):
            r = client.post(
                "/api/v1/advisor/rag/eu-ai-act-nis2-query",
                headers=_rag_headers(),
                json={"question_de": "Risikomanagement Hochrisiko KI?", "tenant_id": tid},
            )
    finally:
        reset_eu_reg_document_store_for_tests()

    assert r.status_code == 200
    spans = otel_exporter.get_finished_spans()
    names = sorted({s.name for s in spans})
    assert "rag.generation" in names
    assert "rag.query_received" in names
    assert "rag.retrieval" in names
    assert any(n.startswith("http ") for n in names)
    # LLM span appears when ``generate_eu_reg_rag_llm_output`` calls ``safe_llm_call_sync``;
    # this test mocks generation, so we only assert RAG + HTTP spans and log correlation.

    log_lines = [r.getMessage() for r in caplog.records if "rag_query_event" in r.getMessage()]
    assert len(log_lines) >= 2
    payload = json.loads(log_lines[-1].split("rag_query_event ", 1)[1])
    log_tid = payload.get("trace_id")
    assert log_tid
    span_trace_ids = {format(s.context.trace_id, "032x") for s in spans}
    assert log_tid in span_trace_ids


def test_activity_load_snapshot_continues_api_trace_carrier(
    otel_exporter: object,
) -> None:
    tracer = trace.get_tracer("test.manual")
    carrier: dict[str, str] = {}
    with tracer.start_as_current_span("synthetic_http_board_report"):
        inject_trace_carrier(carrier)
    assert carrier.get("traceparent")

    wf_in = BoardReportWorkflowInput(
        tenant_id="otel-wf-tenant",
        user_role_for_opa="tenant_admin",
        otel_trace_carrier=carrier,
    )
    with patch(
        "app.workflows.board_report_activities.load_tenant_snapshot_for_board_report",
        return_value={"primary_ai_system_id": None},
    ):
        load_tenant_board_snapshot_activity(wf_in)

    spans = otel_exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert "synthetic_http_board_report" in names
    assert "activity.load_snapshot" in names
    trace_ids = {format(s.context.trace_id, "032x") for s in spans}
    assert len(trace_ids) == 1
