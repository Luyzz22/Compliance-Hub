"""Board report: second LLM step for governance maturity summary + payload persistence."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.llm_models import LLMProvider, LLMResponse, LLMTaskType
from app.main import app

client = TestClient(app)
_GOLDEN = Path(__file__).resolve().parent / "fixtures" / "governance_maturity_summary_golden"


def _h(tid: str) -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tid}


def test_board_report_governance_summary_then_markdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_CROSS_REGULATION_LLM_ASSIST", "false")

    tid = f"br-gov-{uuid.uuid4().hex[:10]}"
    md = "## Executive Overview\n\nStub.\n"
    summary_raw = (_GOLDEN / "response_basic_low.json").read_text(encoding="utf-8")
    chain: list[LLMTaskType] = []

    def _fake_route_and_call(self, task_type, prompt, tenant_id, **kwargs):
        chain.append(task_type)
        if task_type == LLMTaskType.GOVERNANCE_MATURITY_BOARD_SUMMARY:
            return LLMResponse(
                text=summary_raw,
                provider=LLMProvider.CLAUDE,
                model_id="test-model",
            )
        return LLMResponse(
            text=md,
            provider=LLMProvider.CLAUDE,
            model_id="test-model",
        )

    with patch(
        "app.services.llm_router.LLMRouter.route_and_call",
        _fake_route_and_call,
    ):
        r = client.post(
            f"/api/v1/tenants/{tid}/board/ai-compliance-report",
            headers=_h(tid),
            json={"audience_type": "board"},
        )
    assert r.status_code == 201
    assert chain[0] == LLMTaskType.GOVERNANCE_MATURITY_BOARD_SUMMARY
    assert chain[1] == LLMTaskType.AI_COMPLIANCE_BOARD_REPORT

    rid = r.json()["report_id"]
    d = client.get(
        f"/api/v1/tenants/{tid}/board/ai-compliance-reports/{rid}",
        headers=_h(tid),
    )
    assert d.status_code == 200
    payload = d.json()["raw_payload"]
    gmb = payload.get("governance_maturity_board_summary")
    assert gmb is not None
    assert gmb["parse_ok"] is True
    assert "summary" in gmb
    lvl = gmb["summary"]["readiness"]["level"]
    assert lvl in ("basic", "managed", "embedded")
    inp = payload["input"]
    assert inp["governance_maturity_summary"] is not None
    para = inp.get("governance_maturity_executive_paragraph_de") or ""
    assert len(para) >= 80
    dumped = json.dumps(payload)
    assert "governance_maturity_summary" in dumped
