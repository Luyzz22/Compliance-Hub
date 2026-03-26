"""API-Tests: AI-Compliance-Board-Report (Persistenz + Mock-LLM)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.llm_models import LLMProvider, LLMResponse
from app.main import app

client = TestClient(app)


def _h(tid: str) -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tid}


def test_board_report_tenant_path_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")
    tid = "board-kpi-tenant"
    r = client.post(
        "/api/v1/tenants/other-tenant/board/ai-compliance-report",
        headers=_h(tid),
        json={"audience_type": "board"},
    )
    assert r.status_code == 403


def test_board_report_forbidden_when_feature_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "false")
    tid = "board-kpi-tenant"
    r = client.post(
        f"/api/v1/tenants/{tid}/board/ai-compliance-report",
        headers=_h(tid),
        json={"audience_type": "board"},
    )
    assert r.status_code == 403


def test_board_report_create_and_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "false")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    tid = f"br-api-{uuid.uuid4().hex[:10]}"

    md = "## Executive Overview\n\nTestbericht.\n"

    def _fake_route_and_call(self, task_type, prompt, tenant_id, **kwargs):
        return LLMResponse(
            text=md,
            provider=LLMProvider.CLAUDE,
            model_id="test-model",
        )

    with patch(
        "app.services.ai_compliance_board_report_llm.LLMRouter.route_and_call",
        _fake_route_and_call,
    ):
        r = client.post(
            f"/api/v1/tenants/{tid}/board/ai-compliance-report",
            headers=_h(tid),
            json={
                "audience_type": "management",
                "focus_frameworks": ["eu_ai_act"],
                "include_ai_act_only": False,
            },
        )
    assert r.status_code == 201
    body = r.json()
    assert body["rendered_markdown"].startswith("## Executive")
    rid = body["report_id"]

    r2 = client.get(
        f"/api/v1/tenants/{tid}/board/ai-compliance-reports",
        headers=_h(tid),
    )
    assert r2.status_code == 200
    items = r2.json()
    assert any(x["id"] == rid for x in items)

    r3 = client.get(
        f"/api/v1/tenants/{tid}/board/ai-compliance-reports/{rid}",
        headers=_h(tid),
    )
    assert r3.status_code == 200
    assert r3.json()["rendered_markdown"].strip() == md.strip()
