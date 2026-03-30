"""API: start Board Report workflow (Temporal client mocked)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import _sanitize_tenant_id_for_temporal_workflow_id, app
from app.policy.opa_client import PolicyDecision

client = TestClient(app)


def _h(tid: str) -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tid}


@pytest.fixture
def _feature_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")


def test_start_board_report_workflow_path_mismatch(
    _feature_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tid = "wf-tenant-a"
    r = client.post(
        "/api/v1/tenants/other/board-report/workflows/start",
        headers=_h(tid),
        json={},
    )
    assert r.status_code == 403


def test_start_board_report_workflow_opa_denied(
    _feature_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tid = f"wf-opa-{uuid.uuid4().hex[:10]}"
    with patch(
        "app.policy.policy_guard.evaluate_action_policy",
        return_value=PolicyDecision(allowed=False, reason="deny"),
    ):
        r = client.post(
            f"/api/v1/tenants/{tid}/board-report/workflows/start",
            headers=_h(tid),
            json={},
        )
    assert r.status_code == 403


def test_start_board_report_workflow_accepts(
    _feature_on: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tid = f"wf-ok-{uuid.uuid4().hex[:10]}"

    class _Desc:
        run_id = "run-test-1"

    class _Handle:
        async def describe(self):
            return _Desc()

    mock_client = AsyncMock()
    mock_client.start_workflow = AsyncMock(return_value=_Handle())

    async def _fake_get():
        return mock_client

    with (
        patch(
            "app.main.get_temporal_client",
            _fake_get,
        ),
        patch(
            "app.main.uuid.uuid4",
            return_value=uuid.UUID("00000000-0000-0000-0000-00000000abcd"),
        ),
    ):
        r = client.post(
            f"/api/v1/tenants/{tid}/board-report/workflows/start",
            headers=_h(tid),
            json={"audience_type": "board"},
        )
    assert r.status_code == 202
    body = r.json()
    safe = _sanitize_tenant_id_for_temporal_workflow_id(tid)
    assert body["workflow_id"] == f"board-report-{safe}-00000000-0000-0000-0000-00000000abcd"
    assert body["run_id"] == "run-test-1"
    mock_client.start_workflow.assert_called_once()
