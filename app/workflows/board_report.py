"""
Deterministic Board Report Temporal workflow (pilot).

LLM and I/O live in activities (board_report_activities.py), not in the workflow body.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import timedelta

from temporalio import workflow


@dataclass
class BoardReportWorkflowInput:
    tenant_id: str
    snapshot_reference: str = "latest"
    audience_type: str = "board"
    primary_ai_system_id: str | None = None
    focus_frameworks: list[str] = field(default_factory=list)
    include_ai_act_only: bool = False
    language: str = "de"
    user_role_for_opa: str = ""
    # W3C trace context (traceparent / tracestate) from API for worker span stitching.
    otel_trace_carrier: dict[str, str] = field(default_factory=dict)


@dataclass
class BoardReportWorkflowResult:
    report_id: str
    workflow_id: str
    run_id: str


@workflow.defn(name="BoardReportWorkflow")
class BoardReportWorkflow:
    @workflow.run
    async def run(self, inp: BoardReportWorkflowInput) -> BoardReportWorkflowResult:
        snapshot = await workflow.execute_activity(
            "load_tenant_board_snapshot_activity",
            inp,
            start_to_close_timeout=timedelta(minutes=10),
        )
        primary_id = inp.primary_ai_system_id or snapshot.get("primary_ai_system_id")
        if not primary_id:
            oami_expl: dict = {}
        else:
            oami_expl = await workflow.execute_activity(
                "generate_explanations_with_langgraph_activity",
                {
                    "tenant_id": inp.tenant_id,
                    "ai_system_id": str(primary_id),
                    "user_role": inp.user_role_for_opa or "",
                    "otel_trace_carrier": dict(inp.otel_trace_carrier or {}),
                },
                start_to_close_timeout=timedelta(minutes=15),
            )
        info = workflow.info()
        wid = info.workflow_id
        report_id = await workflow.execute_activity(
            "persist_board_report_activity",
            {
                "tenant_id": inp.tenant_id,
                "user_role": inp.user_role_for_opa or "",
                "workflow_input": asdict(inp),
                "snapshot": snapshot,
                "oami_explanation": oami_expl,
                "temporal_workflow_id": wid,
                "temporal_run_id": info.run_id,
            },
            start_to_close_timeout=timedelta(minutes=20),
        )
        return BoardReportWorkflowResult(
            report_id=str(report_id),
            workflow_id=wid,
            run_id=info.run_id,
        )
