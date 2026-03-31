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
from app.telemetry.tracing import attach_trace_carrier, start_span
from app.workflows.board_report import BoardReportWorkflowInput


def _carrier_from_mapping(raw: object) -> dict[str, str] | None:
    if not isinstance(raw, dict) or not raw:
        return None
    return {str(k): str(v) for k, v in raw.items() if v is not None}


@activity.defn
def load_tenant_board_snapshot_activity(inp: BoardReportWorkflowInput) -> dict:
    carrier = _carrier_from_mapping(inp.otel_trace_carrier)
    with attach_trace_carrier(carrier):
        with start_span("activity.load_snapshot", tenant_id=inp.tenant_id):
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
    carrier = _carrier_from_mapping(params.get("otel_trace_carrier"))
    with attach_trace_carrier(carrier):
        with start_span("activity.langgraph_explain", tenant_id=tenant_id):
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
    wf_in = params.get("workflow_input")
    carrier = _carrier_from_mapping(
        wf_in.get("otel_trace_carrier") if isinstance(wf_in, dict) else None,
    )
    with attach_trace_carrier(carrier):
        with start_span("activity.persist_board_report", tenant_id=str(params["tenant_id"])):
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
