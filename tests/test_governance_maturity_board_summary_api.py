"""API: POST governance-maturity/board-summary (LLM mock)."""

from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.llm_models import LLMProvider, LLMResponse, LLMTaskType
from app.main import app

client = TestClient(app)
_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "governance_maturity_summary_golden"


def _h(tid: str) -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tid}


def test_governance_maturity_board_summary_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")

    tid = f"gm-bs-{uuid.uuid4().hex[:10]}"
    raw = (_FIXTURES / "response_basic_low.json").read_text(encoding="utf-8")

    def _fake_route_and_call(self, task_type, prompt, tenant_id, **kwargs):
        assert task_type == LLMTaskType.GOVERNANCE_MATURITY_BOARD_SUMMARY
        return LLMResponse(
            text=raw,
            provider=LLMProvider.CLAUDE,
            model_id="test-model",
        )

    with patch(
        "app.services.llm_router.LLMRouter.route_and_call",
        _fake_route_and_call,
    ):
        r = client.post(
            f"/api/v1/tenants/{tid}/governance-maturity/board-summary",
            headers=_h(tid),
        )
    assert r.status_code == 200
    body = r.json()
    assert body["parse_ok"] is True
    assert "executive_overview_governance_maturity_de" in body
    assert len(body["executive_overview_governance_maturity_de"]) >= 80
    assert body["summary"]["readiness"]["level"] in ("basic", "managed", "embedded")


def test_governance_maturity_board_summary_forbidden_when_feature_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "false")
    tid = "gm-bs-off"
    r = client.post(
        f"/api/v1/tenants/{tid}/governance-maturity/board-summary",
        headers=_h(tid),
    )
    assert r.status_code == 403


def test_governance_maturity_board_summary_tenant_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "true")
    r = client.post(
        "/api/v1/tenants/other-tenant/governance-maturity/board-summary",
        headers=_h("board-kpi-tenant"),
    )
    assert r.status_code == 403
