"""Tests: OPA client (mocked HTTP) and FastAPI policy guard."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.policy.opa_client import PolicyDecision, evaluate_action_policy
from app.policy.policy_guard import enforce_action_policy
from app.policy.user_context import UserPolicyContext


class _FakeHttpClient:
    def __init__(self, result_body: dict) -> None:
        self._body = result_body

    def __enter__(self) -> _FakeHttpClient:
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def post(self, url: str, json: dict | None = None) -> MagicMock:
        r = MagicMock()
        r.json.return_value = self._body
        r.raise_for_status = MagicMock()
        return r


def test_evaluate_action_policy_disabled_allows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPA_URL", raising=False)
    d = evaluate_action_policy(
        {"tenant_id": "t1", "user_role": "tenant_user", "action": "x", "risk_score": 0.1},
    )
    assert d.allowed is True
    assert "disabled" in d.reason.lower() or d.reason == "opa_disabled"


def test_evaluate_action_policy_strict_missing_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPA_URL", raising=False)
    monkeypatch.setenv("COMPLIANCEHUB_OPA_STRICT_MISSING", "1")
    d = evaluate_action_policy(
        {"tenant_id": "t1", "user_role": "tenant_user", "action": "x", "risk_score": 0.1},
    )
    assert d.allowed is False


def test_evaluate_action_policy_opa_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPA_URL", "http://localhost:8181")
    monkeypatch.setenv("OPA_POLICY_PATH", "/v1/data/compliancehub/allow_action")
    with patch(
        "app.policy.opa_client.httpx.Client",
        return_value=_FakeHttpClient({"result": True}),
    ):
        d = evaluate_action_policy(
            {
                "tenant_id": "t1",
                "user_role": "tenant_user",
                "action": "call_llm_explain_readiness",
                "risk_score": 0.2,
            },
        )
    assert d.allowed is True


def test_evaluate_action_policy_opa_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPA_URL", "http://localhost:8181")
    with patch(
        "app.policy.opa_client.httpx.Client",
        return_value=_FakeHttpClient({"result": False}),
    ):
        d = evaluate_action_policy(
            {"tenant_id": "t1", "user_role": "viewer", "action": "x", "risk_score": 0.1},
        )
    assert d.allowed is False


def test_enforce_action_policy_raises_403() -> None:
    with patch(
        "app.policy.policy_guard.evaluate_action_policy",
        return_value=PolicyDecision(allowed=False, reason="opa_deny"),
    ):
        with pytest.raises(HTTPException) as ei:
            enforce_action_policy(
                "generate_board_report",
                UserPolicyContext(tenant_id="t1", user_role="tenant_admin"),
                risk_score=0.5,
            )
    assert ei.value.status_code == 403
