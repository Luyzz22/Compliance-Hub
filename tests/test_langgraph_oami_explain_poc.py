"""LangGraph OAMI explain PoC: contract shape, fallback, API + OPA wiring."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.ai_system_models import (
    AIActCategory,
    AISystemCriticality,
    AISystemRiskLevel,
    DataSensitivity,
)
from app.db import SessionLocal
from app.llm.exceptions import LLMContractViolation
from app.main import app
from app.operational_monitoring_models import OamiExplanationOut
from app.policy.opa_client import PolicyDecision
from app.services.oami_explanation import explain_system_oami_de
from app.services.operational_monitoring_index import compute_system_monitoring_index


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _headers(tenant_id: str) -> dict[str, str]:
    return {"x-api-key": "test-api-key", "x-tenant-id": tenant_id}


def _create_system(client: TestClient, tenant_id: str, system_id: str) -> None:
    payload = {
        "id": system_id,
        "name": "LangGraph PoC System",
        "description": "Test",
        "business_unit": "BU",
        "risk_level": AISystemRiskLevel.high.value,
        "ai_act_category": AIActCategory.high_risk.value,
        "gdpr_dpia_required": True,
        "criticality": AISystemCriticality.high.value,
        "data_sensitivity": DataSensitivity.internal.value,
        "has_incident_runbook": True,
        "has_supplier_risk_register": True,
        "has_backup_runbook": True,
    }
    r = client.post("/api/v1/ai-systems", json=payload, headers=_headers(tenant_id))
    assert r.status_code == 200, r.text


def test_oami_explain_poc_api_404_when_flag_off(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ENABLE_LANGGRAPH_POC", raising=False)
    tid = f"lg-poc-{uuid.uuid4().hex[:10]}"
    r = client.post(
        f"/api/v1/tenants/{tid}/agents/oami-explain-poc",
        headers=_headers(tid),
        json={"ai_system_id": "any", "window_days": 90},
    )
    assert r.status_code == 404


def test_oami_explain_poc_api_403_when_opa_denies(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_LANGGRAPH_POC", "true")
    tid = f"lg-poc-{uuid.uuid4().hex[:10]}"
    _create_system(client, tid, "sys-lg-1")
    with patch(
        "app.policy.policy_guard.evaluate_action_policy",
        return_value=PolicyDecision(allowed=False, reason="deny"),
    ):
        r = client.post(
            f"/api/v1/tenants/{tid}/agents/oami-explain-poc",
            headers=_headers(tid),
            json={"ai_system_id": "sys-lg-1", "window_days": 90},
        )
        assert r.status_code == 403


def test_oami_explain_poc_graph_fallback_matches_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.agents.langgraph.oami_explain_poc import run_oami_explain_poc

    def _boom(*_a: object, **_k: object) -> OamiExplanationOut:
        raise LLMContractViolation("forced")

    monkeypatch.setattr(
        "app.agents.langgraph.oami_explain_poc.safe_llm_call_sync",
        _boom,
    )
    tid = f"lg-graph-{uuid.uuid4().hex[:10]}"
    sid = f"sys-{uuid.uuid4().hex[:8]}"
    with SessionLocal() as session:
        from app.models_db import AISystemTable

        row = AISystemTable(
            id=sid,
            tenant_id=tid,
            name="LG",
            description="d",
            business_unit="BU",
            risk_level="high",
            ai_act_category="high_risk",
            gdpr_dpia_required=True,
            criticality="high",
            data_sensitivity="internal",
            has_incident_runbook=True,
            has_supplier_risk_register=True,
            has_backup_runbook=True,
        )
        session.add(row)
        session.commit()

        idx = compute_system_monitoring_index(session, tid, sid, window_days=90)
        expected = explain_system_oami_de(idx.model_copy(update={"explanation": None}))

        out = run_oami_explain_poc(session, tenant_id=tid, ai_system_id=sid, window_days=90)
        assert out.summary_de == expected.summary_de
        assert out.drivers_de == expected.drivers_de


def test_oami_explain_poc_graph_llm_path_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.agents.langgraph.oami_explain_poc import run_oami_explain_poc

    fixed = OamiExplanationOut(
        summary_de="LLM summary",
        drivers_de=["d1"],
        monitoring_gap_de="gap",
    )

    def _fake(*_a: object, **_k: object) -> OamiExplanationOut:
        return fixed

    monkeypatch.setattr(
        "app.agents.langgraph.oami_explain_poc.safe_llm_call_sync",
        _fake,
    )
    tid = f"lg-llm-{uuid.uuid4().hex[:10]}"
    sid = f"sys-{uuid.uuid4().hex[:8]}"
    with SessionLocal() as session:
        from app.models_db import AISystemTable

        session.add(
            AISystemTable(
                id=sid,
                tenant_id=tid,
                name="LG",
                description="d",
                business_unit="BU",
                risk_level="high",
                ai_act_category="high_risk",
                gdpr_dpia_required=True,
                criticality="high",
                data_sensitivity="internal",
                has_incident_runbook=True,
                has_supplier_risk_register=True,
                has_backup_runbook=True,
            ),
        )
        session.commit()
        out = run_oami_explain_poc(session, tenant_id=tid, ai_system_id=sid, window_days=90)
    assert out.model_dump() == fixed.model_dump()


def test_oami_explain_langgraph_poc_global_path_200(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``POST /api/v1/oami-explain-langgraph-poc`` uses x-tenant-id; tenant in path not required."""
    monkeypatch.setenv("ENABLE_LANGGRAPH_POC", "true")
    tid = f"lg-glob-{uuid.uuid4().hex[:10]}"
    sid = "sys-lg-global"
    _create_system(client, tid, sid)

    fixed = OamiExplanationOut(
        summary_de="API summary",
        drivers_de=["x"],
        monitoring_gap_de=None,
    )

    def _fake(*_a: object, **_k: object) -> OamiExplanationOut:
        return fixed

    monkeypatch.setattr(
        "app.agents.langgraph.oami_explain_poc.safe_llm_call_sync",
        _fake,
    )
    r = client.post(
        "/api/v1/oami-explain-langgraph-poc",
        headers=_headers(tid),
        json={"ai_system_id": sid, "window_days": 90},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary_de"] == "API summary"
    assert body["drivers_de"] == ["x"]


def test_oami_explain_langgraph_poc_global_403_when_opa_denies(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENABLE_LANGGRAPH_POC", "true")
    tid = f"lg-g403-{uuid.uuid4().hex[:10]}"
    _create_system(client, tid, "sys-g403")
    with patch(
        "app.policy.policy_guard.evaluate_action_policy",
        return_value=PolicyDecision(allowed=False, reason="deny"),
    ):
        r = client.post(
            "/api/v1/oami-explain-langgraph-poc",
            headers=_headers(tid),
            json={"ai_system_id": "sys-g403", "window_days": 90},
        )
        assert r.status_code == 403
