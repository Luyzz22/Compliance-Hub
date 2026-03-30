"""Unit-style tests: LangGraph activity uses guardrailed path; OPA enforced."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.operational_monitoring_models import OamiExplanationOut
from app.policy.opa_client import PolicyDecision


def test_generate_langgraph_activity_opa_denied_raises() -> None:
    from temporalio.exceptions import ApplicationError

    from app.workflows.board_report_activities import generate_explanations_with_langgraph_activity

    with patch(
        "app.workflows.board_report_activities.evaluate_action_policy",
        return_value=PolicyDecision(allowed=False, reason="deny"),
    ):
        with pytest.raises(ApplicationError, match="OPA denied"):
            generate_explanations_with_langgraph_activity(
                {
                    "tenant_id": "t1",
                    "ai_system_id": "sys-1",
                    "user_role": "tenant_admin",
                },
            )


def test_generate_langgraph_activity_calls_poc_with_user_role() -> None:
    from app.workflows.board_report_activities import generate_explanations_with_langgraph_activity

    fake_out = OamiExplanationOut(
        summary_de="s",
        drivers_de=["a"],
        monitoring_gap_de=None,
    )
    mock_session = MagicMock()
    with (
        patch(
            "app.workflows.board_report_activities.evaluate_action_policy",
            return_value=PolicyDecision(allowed=True, reason="ok"),
        ),
        patch(
            "app.workflows.board_report_activities.SessionLocal",
            return_value=mock_session,
        ),
        patch(
            "app.workflows.board_report_activities.run_oami_explain_poc",
            return_value=fake_out,
        ) as mock_poc,
    ):
        out = generate_explanations_with_langgraph_activity(
            {
                "tenant_id": "t-opa",
                "ai_system_id": "sys-9",
                "user_role": "tenant_admin",
            },
        )
    mock_poc.assert_called_once()
    call_kw = mock_poc.call_args.kwargs
    assert call_kw["tenant_id"] == "t-opa"
    assert call_kw["ai_system_id"] == "sys-9"
    assert call_kw["user_role"] == "tenant_admin"
    assert out["summary_de"] == "s"
