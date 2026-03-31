"""Client/Mandant-level AI Compliance Board Report workflow (Wave 13).

Mirrors the tenant-level BoardReportWorkflow but scoped to a single
client_id (Mandant) within a Kanzlei-tenant.  Aggregates AiSystem
inventory + GRC records and synthesises a German advisory board report.

LLM and I/O live in activities / service layer, not in the workflow body.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow


@dataclass
class ClientBoardReportInput:
    tenant_id: str
    client_id: str
    reporting_period: str = ""
    system_filter: list[str] = field(default_factory=list)
    language: str = "de"
    user_role_for_opa: str = ""
    otel_trace_carrier: dict[str, str] = field(default_factory=dict)


@dataclass
class ClientBoardReportResult:
    report_id: str
    workflow_id: str
    tenant_id: str
    client_id: str
    reporting_period: str
    systems_included: int


@workflow.defn(name="ClientBoardReportWorkflow")
class ClientBoardReportWorkflow:
    @workflow.run
    async def run(self, inp: ClientBoardReportInput) -> ClientBoardReportResult:
        snapshot = await workflow.execute_activity(
            "aggregate_client_board_data_activity",
            {
                "tenant_id": inp.tenant_id,
                "client_id": inp.client_id,
                "reporting_period": inp.reporting_period,
                "system_filter": inp.system_filter,
            },
            start_to_close_timeout=timedelta(minutes=10),
        )

        report = await workflow.execute_activity(
            "synthesise_client_board_report_activity",
            {
                "tenant_id": inp.tenant_id,
                "client_id": inp.client_id,
                "reporting_period": inp.reporting_period,
                "snapshot": snapshot,
                "language": inp.language,
                "user_role": inp.user_role_for_opa,
            },
            start_to_close_timeout=timedelta(minutes=15),
        )

        info = workflow.info()
        return ClientBoardReportResult(
            report_id=report.get("report_id", ""),
            workflow_id=info.workflow_id,
            tenant_id=inp.tenant_id,
            client_id=inp.client_id,
            reporting_period=inp.reporting_period,
            systems_included=report.get("systems_included", 0),
        )
