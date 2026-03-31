"""Wave 5: AI Act evidence list/detail/export (tenant-scoped, metadata only)."""

from __future__ import annotations

import csv
import io
import json
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models_db import Base
from app.policy.opa_client import PolicyDecision
from app.repositories.ai_compliance_board_reports import AiComplianceBoardReportRepository
from app.repositories.audit import AuditRepository


@contextmanager
def patch_policy_allow():
    with patch(
        "app.policy.policy_guard.evaluate_action_policy",
        return_value=PolicyDecision(allowed=True, reason="test"),
    ):
        yield


@contextmanager
def patch_policy_deny():
    with patch(
        "app.policy.policy_guard.evaluate_action_policy",
        return_value=PolicyDecision(allowed=False, reason="deny"),
    ):
        yield


@pytest.fixture
def evidence_tenant_id() -> str:
    return f"evidence-tenant-{uuid.uuid4().hex[:10]}"


def _headers(tenant_id: str) -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
        "x-opa-user-role": "compliance_officer",
    }


def _seed_evidence_rows(session: Session, tenant_id: str) -> tuple[str, str, str, str]:
    audit = AuditRepository(session)
    rag_low = audit.log_event(
        tenant_id=tenant_id,
        actor_type="advisor",
        actor_id="adv-1",
        entity_type="advisor_regulatory_rag",
        entity_id=tenant_id,
        action="query",
        metadata={
            "citation_count": 0,
            "query_sha256": "aa" * 32,
            "confidence_level": "low",
            "tenant_guidance_citation_count": 0,
            "citation_doc_ids": [],
            "opa_user_role": "advisor",
        },
    )
    rag_high = audit.log_event(
        tenant_id=tenant_id,
        actor_type="advisor",
        actor_id="adv-1",
        entity_type="advisor_regulatory_rag",
        entity_id=tenant_id,
        action="query",
        metadata={
            "citation_count": 2,
            "query_sha256": "bb" * 32,
            "confidence_level": "high",
            "tenant_guidance_citation_count": 1,
            "citation_doc_ids": ["doc-a", "doc-b"],
            "opa_user_role": "advisor",
        },
    )
    wf = audit.log_event(
        tenant_id=tenant_id,
        actor_type="api_key",
        actor_id=None,
        entity_type="temporal_board_report_workflow",
        entity_id=f"board-report-{uuid.uuid4().hex[:8]}",
        action="started",
        metadata={"task_queue": "q", "opa_user_role": "tenant_admin"},
    )
    audit.log_event(
        tenant_id=tenant_id,
        actor_type="llm",
        actor_id=None,
        entity_type="llm_contract_violation",
        entity_id=tenant_id,
        action="contract_violation",
        metadata={
            "llm_action_name": "generate_board_report",
            "task_type": "ai_compliance_board_report",
            "contract_schema": "EuRegRagLlmOutput",
            "error_class": "LLMContractViolation",
        },
    )
    repo = AiComplianceBoardReportRepository(session)
    br = repo.create(
        tenant_id=tenant_id,
        created_by="temporal:board_report_workflow",
        title="Test Temporal Report",
        audience_type="board",
        raw_payload={
            "version": 2,
            "source": "temporal_board_report_workflow",
            "temporal_workflow_id": "wf-1",
            "temporal_run_id": "run-1",
            "langgraph_oami_explanation": {"ok": True},
        },
        rendered_markdown="# Secret markdown body must not appear in evidence API",
        rendered_html=None,
    )
    return rag_low.id, rag_high.id, wf.id, br.id


@pytest.fixture
def seeded(evidence_tenant_id: str) -> tuple[str, str, str, str]:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        ids = _seed_evidence_rows(session, evidence_tenant_id)
    return ids


def test_evidence_list_filters(
    monkeypatch: pytest.MonkeyPatch,
    evidence_tenant_id: str,
    seeded: tuple[str, str, str, str],
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_ACT_EVIDENCE_VIEWS", "true")
    with patch_policy_allow():
        client = TestClient(app)
        now = datetime.now(UTC)
        frm = (now - timedelta(days=1)).isoformat()
        to = (now + timedelta(days=1)).isoformat()
        r = client.get(
            "/api/v1/evidence/ai-act/events",
            params={
                "tenant_id": evidence_tenant_id,
                "from_ts": frm,
                "to_ts": to,
                "event_types": "rag_query",
                "confidence_level": "low",
            },
            headers=_headers(evidence_tenant_id),
        )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["event_type"] == "rag_query"
    assert body["items"][0]["confidence_level"] == "low"


def test_evidence_detail_rag_no_content_leak(
    monkeypatch: pytest.MonkeyPatch,
    evidence_tenant_id: str,
    seeded: tuple[str, str, str, str],
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_ACT_EVIDENCE_VIEWS", "true")
    rag_high_id = seeded[1]
    with patch_policy_allow():
        client = TestClient(app)
        r = client.get(
            f"/api/v1/evidence/ai-act/events/audit:{rag_high_id}",
            params={"tenant_id": evidence_tenant_id},
            headers=_headers(evidence_tenant_id),
        )
    assert r.status_code == 200
    d = r.json()
    assert d["rag"] is not None
    assert d["rag"]["citation_doc_ids"] == ["doc-a", "doc-b"]
    assert d["rag"]["tenant_guidance_citation_count"] == 1
    raw = json.dumps(d)
    assert "Secret markdown" not in raw
    assert "question" not in raw.lower() or "query_sha256" in raw


def test_evidence_export_json_no_pii_fields(
    monkeypatch: pytest.MonkeyPatch,
    evidence_tenant_id: str,
    seeded: tuple[str, str, str, str],
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_ACT_EVIDENCE_VIEWS", "true")
    with patch_policy_allow():
        client = TestClient(app)
        r = client.get(
            "/api/v1/evidence/ai-act/export",
            params={"tenant_id": evidence_tenant_id, "format": "json"},
            headers=_headers(evidence_tenant_id),
        )
    assert r.status_code == 200
    data = json.loads(r.content.decode("utf-8"))
    blob = json.dumps(data)
    assert "question_preview" not in blob
    assert "Secret markdown" not in blob


def test_evidence_export_csv_roundtrip(
    monkeypatch: pytest.MonkeyPatch,
    evidence_tenant_id: str,
    seeded: tuple[str, str, str, str],
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_ACT_EVIDENCE_VIEWS", "true")
    with patch_policy_allow():
        client = TestClient(app)
        r = client.get(
            "/api/v1/evidence/ai-act/export",
            params={"tenant_id": evidence_tenant_id, "format": "csv"},
            headers=_headers(evidence_tenant_id),
        )
    assert r.status_code == 200
    text = r.content.decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    assert len(rows) >= 2
    header = rows[0]
    assert "event_id" in header
    assert "summary_de" in header


def test_evidence_opa_denied(
    monkeypatch: pytest.MonkeyPatch,
    evidence_tenant_id: str,
    seeded: tuple[str, str, str, str],
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_ACT_EVIDENCE_VIEWS", "true")
    with patch_policy_deny():
        client = TestClient(app)
        r = client.get(
            "/api/v1/evidence/ai-act/events",
            params={"tenant_id": evidence_tenant_id},
            headers=_headers(evidence_tenant_id),
        )
    assert r.status_code == 403


def test_evidence_unknown_event_type_422(
    monkeypatch: pytest.MonkeyPatch,
    evidence_tenant_id: str,
    seeded: tuple[str, str, str, str],
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_ACT_EVIDENCE_VIEWS", "true")
    with patch_policy_allow():
        client = TestClient(app)
        r = client.get(
            "/api/v1/evidence/ai-act/events",
            params={"tenant_id": evidence_tenant_id, "event_types": "not_a_real_type"},
            headers=_headers(evidence_tenant_id),
        )
    assert r.status_code == 422
