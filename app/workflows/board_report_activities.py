"""Temporal activities for BoardReportWorkflow (DB, OPA, LangGraph, guardrailed LLM)."""

from __future__ import annotations

from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.agents.langgraph.oami_explain_poc import run_oami_explain_poc
from app.db import SessionLocal
from app.policy.opa_client import evaluate_action_policy
from app.services.temporal_board_report import (
    load_tenant_snapshot_for_board_report,
    persist_versioned_board_report_from_workflow,
)
from app.workflows.board_report import BoardReportWorkflowInput


@activity.defn
def load_tenant_board_snapshot_activity(inp: BoardReportWorkflowInput) -> dict:
    session = SessionLocal()
    try:
        return load_tenant_snapshot_for_board_report(session, inp)
    finally:
        session.close()


@activity.defn
def generate_explanations_with_langgraph_activity(params: dict) -> dict:
    tenant_id = str(params["tenant_id"])
    ai_system_id = str(params["ai_system_id"])
    user_role = str(params.get("user_role") or "")
    decision = evaluate_action_policy(
        {
            "tenant_id": tenant_id,
            "user_role": user_role or "tenant_admin",
            "action": "call_langgraph_oami_explain",
            "risk_score": 0.4,
        },
    )
    if not decision.allowed:
        raise ApplicationError(
            "OPA denied call_langgraph_oami_explain",
            non_retryable=True,
        )
    session = SessionLocal()
    try:
        out = run_oami_explain_poc(
            session,
            tenant_id=tenant_id,
            ai_system_id=ai_system_id,
            window_days=90,
            user_role=user_role,
        )
        return out.model_dump(mode="json")
    finally:
        session.close()


@activity.defn
def persist_board_report_activity(params: dict) -> str:
    session = SessionLocal()
    try:
        return persist_versioned_board_report_from_workflow(
            session,
            tenant_id=str(params["tenant_id"]),
            user_role=str(params.get("user_role") or ""),
            workflow_input_dict=dict(params["workflow_input"]),
            snapshot=dict(params["snapshot"]),
            oami_explanation=dict(params.get("oami_explanation") or {}),
            temporal_workflow_id=str(params["temporal_workflow_id"]),
            temporal_run_id=str(params.get("temporal_run_id") or ""),
        )
    except PermissionError as exc:
        raise ApplicationError(str(exc), non_retryable=True) from exc
    finally:
        session.close()
