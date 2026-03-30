"""Wave 3: EU regulatory RAG — retriever, pipeline, API + OPA + observability."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from haystack import Document
from haystack.components.retrievers import InMemoryBM25Retriever
from haystack.document_stores.in_memory import InMemoryDocumentStore

from app.main import app
from app.policy.opa_client import PolicyDecision
from app.rag.models import EuRegRagLlmCitation, EuRegRagLlmOutput
from app.rag.pipelines.eu_ai_act_nis2_pipeline import run_eu_ai_act_nis2_pipeline
from app.rag.store import (
    replace_eu_reg_document_store_for_tests,
    reset_eu_reg_document_store_for_tests,
)

client = TestClient(app)


def _rag_headers() -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-advisor-id": "advisor-rag-test",
    }


@pytest.fixture
def synthetic_reg_store() -> InMemoryDocumentStore:
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
                    "article": "9",
                    "rag_scope": "global",
                },
            ),
            Document(
                id="nis2-meldung-chunk-0",
                content=(
                    "Wesentliche Einrichtungen müssen Vorfälle unverzüglich den Behörden melden, "
                    "wenn der Betrieb erheblich beeinträchtigt ist."
                ),
                meta={
                    "source": "NIS2 (Pilot)",
                    "section": "Meldung von Vorfällen",
                    "article": "21",
                    "rag_scope": "global",
                },
            ),
        ],
    )
    return store


def test_bm25_retriever_returns_nis2_doc(synthetic_reg_store: InMemoryDocumentStore) -> None:
    retriever = InMemoryBM25Retriever(
        document_store=synthetic_reg_store,
        top_k=3,
        filters={"field": "rag_scope", "operator": "==", "value": "global"},
    )
    out = retriever.run(query="NIS2 Meldung Behörden Vorfall")
    ids = [d.id for d in out["documents"]]
    assert "nis2-meldung-chunk-0" in ids


def test_pipeline_mock_llm_includes_expected_citation(
    synthetic_reg_store: InMemoryDocumentStore,
) -> None:
    fixed = EuRegRagLlmOutput(
        answer_de="Laut Kurzfragment müssen Vorfälle unverzüglich gemeldet werden.",
        citations=[
            EuRegRagLlmCitation(
                doc_id="nis2-meldung-chunk-0",
                source="NIS2 (Pilot)",
                section="Meldung von Vorfällen",
            ),
        ],
    )

    with patch(
        "app.rag.pipelines.eu_ai_act_nis2_pipeline.generate_eu_reg_rag_llm_output",
        return_value=fixed,
    ):
        pr = run_eu_ai_act_nis2_pipeline(
            question_de="NIS2 Meldung Behörden Vorfall unverzüglich",
            tenant_id="tenant-rag-1",
            user_role="advisor",
            document_store=synthetic_reg_store,
            session=None,
            advisor_id="adv-1",
        )
    assert pr.structured["answer_de"]
    assert pr.structured["citations"][0]["doc_id"] == "nis2-meldung-chunk-0"
    assert any(d.id == "nis2-meldung-chunk-0" for d in pr.documents_for_prompt)


def test_log_rag_query_event_called_twice(
    synthetic_reg_store: InMemoryDocumentStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_RAG_BM25_MIN_SCORE", "0.01")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_CONFIDENCE_HIGH_MIN_SCORE", "0.01")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_CONFIDENCE_GAP_MIN", "0.0")
    fixed = EuRegRagLlmOutput(answer_de="ok", citations=[])
    phases: list[str] = []

    def _capture(**kwargs: object) -> None:
        phases.append(str(kwargs.get("phase")))

    with (
        patch(
            "app.rag.pipelines.eu_ai_act_nis2_pipeline.log_rag_query_event",
            side_effect=_capture,
        ),
        patch(
            "app.rag.pipelines.eu_ai_act_nis2_pipeline.generate_eu_reg_rag_llm_output",
            return_value=fixed,
        ),
    ):
        run_eu_ai_act_nis2_pipeline(
            question_de="NIS2 Meldung Behörden Vorfall unverzüglich",
            tenant_id="t1",
            user_role="advisor",
            document_store=synthetic_reg_store,
            session=None,
            advisor_id="adv-x",
        )
    assert phases == ["retrieval_complete", "response_complete"]


def test_tenant_overlay_citation_flag(
    synthetic_reg_store: InMemoryDocumentStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_RAG_BM25_MIN_SCORE", "0.01")
    tid = "tenant-overlay-1"
    synthetic_reg_store.write_documents(
        [
            Document(
                id="acme-nis2-note-chunk-0",
                content="Mandant ACME: Bei NIS2-Meldungen zuerst internen Krisenstab informieren.",
                meta={
                    "source": "ACME intern",
                    "section": "Playbook",
                    "rag_scope": "tenant_guidance",
                    "tenant_id": tid,
                },
            ),
        ],
    )
    fixed = EuRegRagLlmOutput(
        answer_de="Zuerst Krisenstab laut Mandantenleitfaden.",
        citations=[
            EuRegRagLlmCitation(
                doc_id="acme-nis2-note-chunk-0",
                source="ACME intern",
                section="Playbook",
            ),
        ],
    )
    gen = "app.rag.pipelines.eu_ai_act_nis2_pipeline.generate_eu_reg_rag_llm_output"
    with patch(gen, return_value=fixed):
        pr = run_eu_ai_act_nis2_pipeline(
            question_de="NIS2 Meldung Krisenstab ACME",
            tenant_id=tid,
            user_role="advisor",
            document_store=synthetic_reg_store,
            session=None,
        )
    assert any(d.id == "acme-nis2-note-chunk-0" for d in pr.documents_for_prompt)
    from app.rag.service import run_advisor_eu_reg_rag

    with patch(gen, return_value=fixed):
        out = run_advisor_eu_reg_rag(
            question_de="NIS2 Meldung Krisenstab ACME",
            tenant_id=tid,
            user_role="advisor",
            advisor_id="adv",
            session=None,
            document_store=synthetic_reg_store,
        )
    assert out.citations
    assert out.citations[0].is_tenant_specific is True


def test_confidence_high_when_strong_hit(
    synthetic_reg_store: InMemoryDocumentStore,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_RAG_BM25_MIN_SCORE", "0.01")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_CONFIDENCE_HIGH_MIN_SCORE", "0.01")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_CONFIDENCE_GAP_MIN", "0.0")
    fixed = EuRegRagLlmOutput(answer_de="Antwort", citations=[])
    with patch("app.rag.generation.generate_eu_reg_rag_llm_output", return_value=fixed):
        pr = run_eu_ai_act_nis2_pipeline(
            question_de="NIS2 Meldung Behörden Vorfall unverzüglich",
            tenant_id="t-high",
            user_role="advisor",
            document_store=synthetic_reg_store,
            session=None,
        )
    assert pr.confidence_level == "high"


def test_confidence_low_safe_answer_without_llm() -> None:
    empty_store = InMemoryDocumentStore()
    with patch(
        "app.rag.pipelines.eu_ai_act_nis2_pipeline.generate_eu_reg_rag_llm_output",
    ) as mock_llm:
        pr = run_eu_ai_act_nis2_pipeline(
            question_de="NIS2 Meldung Behörden Vorfall unverzüglich",
            tenant_id="t-low",
            user_role="advisor",
            document_store=empty_store,
            session=None,
        )
    mock_llm.assert_not_called()
    assert pr.used_llm is False
    assert pr.confidence_level == "low"
    assert "keine eindeutigen" in pr.structured["answer_de"].lower()
    assert pr.notes_de


def test_advisor_rag_api_opa_denies_no_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_reg_store: InMemoryDocumentStore,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_COMPLIANCE_RAG_KNOWLEDGE_HUB", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    tid = f"rag-tenant-{uuid.uuid4().hex[:8]}"
    replace_eu_reg_document_store_for_tests(synthetic_reg_store)
    try:
        with (
            patch(
                "app.policy.policy_guard.evaluate_action_policy",
                return_value=PolicyDecision(allowed=False, reason="deny"),
            ),
            patch(
                "app.main.run_advisor_eu_reg_rag",
            ) as mock_svc,
        ):
            r = client.post(
                "/api/v1/advisor/rag/eu-ai-act-nis2-query",
                headers=_rag_headers(),
                json={
                    "question_de": "Was sagt der EU AI Act zum Risikomanagement?",
                    "tenant_id": tid,
                },
            )
    finally:
        reset_eu_reg_document_store_for_tests()
    assert r.status_code == 403
    mock_svc.assert_not_called()


def test_advisor_rag_api_happy_path_mock_llm(
    monkeypatch: pytest.MonkeyPatch,
    synthetic_reg_store: InMemoryDocumentStore,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_COMPLIANCE_RAG_KNOWLEDGE_HUB", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_BM25_MIN_SCORE", "0.01")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_CONFIDENCE_HIGH_MIN_SCORE", "0.01")
    monkeypatch.setenv("COMPLIANCEHUB_RAG_CONFIDENCE_GAP_MIN", "0.0")
    tid = f"rag-tenant-{uuid.uuid4().hex[:8]}"
    replace_eu_reg_document_store_for_tests(synthetic_reg_store)
    fixed = EuRegRagLlmOutput(
        answer_de="Hochrisiko-KI erfordert ein Risikomanagementsystem.",
        citations=[
            EuRegRagLlmCitation(
                doc_id="eu-ai-act-art9-chunk-0",
                source="EU AI Act (Pilot)",
                section="Art. 9 Risikomanagement",
            ),
        ],
    )
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
        ):
            r = client.post(
                "/api/v1/advisor/rag/eu-ai-act-nis2-query",
                headers=_rag_headers(),
                json={
                    "question_de": "EU AI Act Risikomanagement Hochrisiko?",
                    "tenant_id": tid,
                },
            )
    finally:
        reset_eu_reg_document_store_for_tests()
    assert r.status_code == 200
    body = r.json()
    assert "Risiko" in body["answer_de"] or "risiko" in body["answer_de"].lower()
    assert body["citations"]
    assert body["citations"][0]["doc_id"] == "eu-ai-act-art9-chunk-0"
    assert body["citations"][0]["source_id"] == "eu-ai-act-art9-chunk-0"
    assert body["confidence_level"] == "high"
    assert "notes_de" in body
