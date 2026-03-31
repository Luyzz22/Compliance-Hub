"""Integration dispatcher — pick pending jobs, map, deliver, dead-letter.

Simple synchronous loop suitable for in-memory stores and Temporal
activity wrapping.  Keeps retry semantics explicit and deterministic.
"""

from __future__ import annotations

import logging
from typing import Any

from app.grc.models import (
    AiRiskAssessment,
    AiSystem,
    Iso42001GapRecord,
    Nis2ObligationRecord,
)
from app.grc.store import (
    get_ai_system_by_id,
    list_iso42001_gaps,
    list_nis2_obligations,
    list_risks,
)
from app.integrations.connectors import connector_for_target
from app.integrations.mappers import resolve_mapper
from app.integrations.models import (
    MAX_DISPATCH_ATTEMPTS,
    IntegrationJob,
    IntegrationJobStatus,
)
from app.integrations.store import (
    pending_jobs,
    update_job_status,
)

logger = logging.getLogger(__name__)


def _resolve_source_entity(job: IntegrationJob) -> Any | None:
    """Load the source entity from the GRC / AiSystem stores."""
    etype = job.source_entity_type
    eid = job.source_entity_id
    if not etype or not eid:
        return None

    if etype == "AiRiskAssessment":
        for r in list_risks():
            if r.id == eid:
                return r
    elif etype == "Nis2ObligationRecord":
        for r in list_nis2_obligations():
            if r.id == eid:
                return r
    elif etype == "Iso42001GapRecord":
        for r in list_iso42001_gaps():
            if r.id == eid:
                return r
    elif etype == "AiSystemReadinessSnapshot":
        return get_ai_system_by_id(eid)
    elif etype == "ClientBoardReport":
        from app.grc.client_board_report_service import get_report

        return get_report(eid)
    return None


def _build_payload(job: IntegrationJob) -> dict[str, Any] | None:
    """Build the outbound payload for the job."""
    if job.payload:
        return job.payload

    entity = _resolve_source_entity(job)
    if entity is None:
        return None

    mapper = resolve_mapper(job.payload_type.value, job.target.value)
    if mapper is None:
        return None

    if isinstance(entity, (AiRiskAssessment, Nis2ObligationRecord, Iso42001GapRecord, AiSystem)):
        return mapper(entity)

    if hasattr(entity, "model_dump"):
        return mapper(entity.model_dump())
    if isinstance(entity, dict):
        return mapper(entity)
    return None


def dispatch_one(job: IntegrationJob) -> bool:
    """Dispatch a single job.  Returns True on success."""
    payload = _build_payload(job)
    if payload is None:
        logger.warning(
            "integration_dispatch_no_payload",
            extra={"job_id": job.job_id},
        )
        update_job_status(
            job.job_id,
            IntegrationJobStatus.failed,
            dispatch_result="no payload resolved",
        )
        return False

    connector = connector_for_target(job.target.value)
    update_job_status(job.job_id, IntegrationJobStatus.dispatched)

    result = connector.dispatch(job, payload)
    if result.success:
        update_job_status(
            job.job_id,
            IntegrationJobStatus.delivered,
            dispatch_result=result.message,
        )
        return True

    if job.attempt_count >= MAX_DISPATCH_ATTEMPTS:
        update_job_status(
            job.job_id,
            IntegrationJobStatus.dead_letter,
            dispatch_result=result.message,
        )
    else:
        update_job_status(
            job.job_id,
            IntegrationJobStatus.failed,
            dispatch_result=result.message,
        )
    return False


def dispatch_pending() -> dict[str, int]:
    """Process all pending jobs.  Returns counts by outcome."""
    counts: dict[str, int] = {
        "dispatched": 0,
        "delivered": 0,
        "failed": 0,
        "dead_letter": 0,
    }
    jobs = pending_jobs()
    for job in jobs:
        ok = dispatch_one(job)
        if ok:
            counts["delivered"] += 1
        else:
            if job.status == IntegrationJobStatus.dead_letter:
                counts["dead_letter"] += 1
            else:
                counts["failed"] += 1
    return counts
