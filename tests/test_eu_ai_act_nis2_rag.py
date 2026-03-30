"""Wave 3: EU regulatory RAG — retriever, pipeline (mock LLM), API + OPA."""

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
                },
            ),
        ],
    )
    return store


def test_bm25_retriever_returns_nis2_doc(synthetic_reg_store: InMemoryDocumentStore) -> None:
    retriever = InMemoryBM25Retriever(document_store=synthetic_reg_store, top_k=3)
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
        "app.rag.pipelines.eu_ai_act_nis2_pipeline.safe_llm_call_sync",
        return_value=fixed,
    ):
        structured, docs = run_eu_ai_act_nis2_pipeline(
            question_de="NIS2 Meldung Behörden Vorfall unverzüglich",
            tenant_id="tenant-rag-1",
            user_role="advisor",
            document_store=synthetic_reg_store,
            session=None,
        )
    assert structured["answer_de"]
    assert structured["citations"][0]["doc_id"] == "nis2-meldung-chunk-0"
    assert any(d.id == "nis2-meldung-chunk-0" for d in docs)


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
                "app.rag.pipelines.eu_ai_act_nis2_pipeline.safe_llm_call_sync",
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
