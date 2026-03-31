"""Run Temporal worker process: `python -m app.workflows.worker`."""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from app.workflows.board_report import BoardReportWorkflow
from app.workflows.board_report_activities import (
    generate_explanations_with_langgraph_activity,
    load_tenant_board_snapshot_activity,
    persist_board_report_activity,
)
from app.workflows.config import (
    temporal_address,
    temporal_api_key,
    temporal_namespace,
    temporal_task_queue,
    temporal_tls_enabled,
)

logger = logging.getLogger(__name__)


async def _run() -> None:
    logging.basicConfig(level=logging.INFO)
    connect_kwargs: dict = {"namespace": temporal_namespace()}
    key = temporal_api_key()
    if key:
        connect_kwargs["api_key"] = key
        connect_kwargs["tls"] = True
    elif temporal_tls_enabled():
        connect_kwargs["tls"] = True
    client = await Client.connect(temporal_address(), **connect_kwargs)
    tq = temporal_task_queue()
    logger.info("temporal_worker_starting queue=%s namespace=%s", tq, temporal_namespace())
    with ThreadPoolExecutor(max_workers=8) as executor:
        worker = Worker(
            client,
            task_queue=tq,
            workflows=[BoardReportWorkflow],
            activities=[
                load_tenant_board_snapshot_activity,
                generate_explanations_with_langgraph_activity,
                persist_board_report_activity,
            ],
            activity_executor=executor,
        )
        await worker.run()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
