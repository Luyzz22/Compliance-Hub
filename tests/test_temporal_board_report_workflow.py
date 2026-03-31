"""Board Report Temporal path: activity chain on test DB; optional workflow env test."""

from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.db import engine
from app.llm_models import LLMProvider, LLMResponse
from app.policy.opa_client import PolicyDecision
from app.repositories.ai_compliance_board_reports import AiComplianceBoardReportRepository
from app.workflows.board_report import BoardReportWorkflow, BoardReportWorkflowInput
from app.workflows.board_report_activities import (
    generate_explanations_with_langgraph_activity,
    load_tenant_board_snapshot_activity,
    persist_board_report_activity,
)


@pytest.fixture
def temporal_tenant_id(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "false")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_READINESS_SCORE", "false")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    return f"temporal-br-{uuid.uuid4().hex[:12]}"


def _fake_guardrailed(*_args, **_kwargs):
    return LLMResponse(
        text="## Executive Overview\n\nTemporal test report.\n",
        provider=LLMProvider.CLAUDE,
        model_id="test-model",
    )


def test_board_report_activity_chain_creates_report_row(
    temporal_tenant_id: str,
) -> None:
    """Same steps as the workflow, without Ephemeral Temporal (CI-friendly)."""
    wf_in = BoardReportWorkflowInput(
        tenant_id=temporal_tenant_id,
        user_role_for_opa="tenant_admin",
    )
    with (
        patch(
            "app.policy.opa_client.evaluate_action_policy",
            return_value=PolicyDecision(allowed=True, reason="test"),
        ),
        patch(
            "app.services.ai_compliance_board_report_llm.guardrailed_route_and_call_sync",
            _fake_guardrailed,
        ),
    ):
        snapshot = load_tenant_board_snapshot_activity(wf_in)
        oami: dict = {}
        if snapshot.get("primary_ai_system_id"):
            oami = generate_explanations_with_langgraph_activity(
                {
                    "tenant_id": temporal_tenant_id,
                    "ai_system_id": str(snapshot["primary_ai_system_id"]),
                    "user_role": "tenant_admin",
                },
            )
        report_id = persist_board_report_activity(
            {
                "tenant_id": temporal_tenant_id,
                "user_role": "tenant_admin",
                "workflow_input": asdict(wf_in),
                "snapshot": snapshot,
                "oami_explanation": oami,
                "temporal_workflow_id": "test-local-wf",
                "temporal_run_id": "test-local-run",
            },
        )

    with Session(engine) as session:
        row = AiComplianceBoardReportRepository(session).get(report_id, temporal_tenant_id)
    assert row is not None
    assert row.raw_payload.get("source") == "temporal_board_report_workflow"
    assert row.raw_payload.get("version") == 2
    assert "Temporal test report" in (row.rendered_markdown or "")


async def _execute_board_report_workflow(tenant_id: str) -> None:
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    from app.workflows.config import temporal_task_queue

    async with await WorkflowEnvironment.start_time_skipping() as env:
        with ThreadPoolExecutor(max_workers=8) as executor:
            async with Worker(
                env.client,
                task_queue=temporal_task_queue(),
                workflows=[BoardReportWorkflow],
                activities=[
                    load_tenant_board_snapshot_activity,
                    generate_explanations_with_langgraph_activity,
                    persist_board_report_activity,
                ],
                activity_executor=executor,
            ):
                await env.client.execute_workflow(
                    BoardReportWorkflow.run,
                    BoardReportWorkflowInput(
                        tenant_id=tenant_id,
                        user_role_for_opa="tenant_admin",
                    ),
                    id=f"test-br-{uuid.uuid4()}",
                    task_queue=temporal_task_queue(),
                )


def test_board_report_workflow_time_skipping_optional(
    temporal_tenant_id: str,
) -> None:
    """Runs only when the SDK can start the Ephemeral test server (may download a binary)."""
    with (
        patch(
            "app.policy.opa_client.evaluate_action_policy",
            return_value=PolicyDecision(allowed=True, reason="test"),
        ),
        patch(
            "app.services.ai_compliance_board_report_llm.guardrailed_route_and_call_sync",
            _fake_guardrailed,
        ),
    ):
        try:
            asyncio.run(_execute_board_report_workflow(temporal_tenant_id))
        except RuntimeError as exc:
            msg = str(exc).lower()
            if "test server" in msg or "download" in msg:
                pytest.skip(f"Temporal Ephemeral server not available: {exc}")
            raise

    with Session(engine) as session:
        rows = AiComplianceBoardReportRepository(session).list_for_tenant(
            temporal_tenant_id,
            limit=5,
        )
    assert rows
    assert rows[0].raw_payload.get("source") == "temporal_board_report_workflow"
