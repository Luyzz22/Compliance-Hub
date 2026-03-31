"""Integration dispatcher — pick pending jobs, map, deliver, dead-letter.

Enhanced with configurable throttling, exponential backoff, priority,
and connector-specific artifact/envelope refs on the job record.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
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
    JobWeight,
)
from app.integrations.store import (
    pending_jobs,
    update_job_status,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dispatcher settings (configurable, not hardcoded)
# ---------------------------------------------------------------------------


@dataclass
class DispatcherSettings:
    max_concurrent_per_target: int = 5
    backoff_base_seconds: float = 1.0
    backoff_max_seconds: float = 30.0
    datev_priority_boost: int = 0
    heavy_job_limit: int = 2
    enable_backoff: bool = True

    _active_per_target: dict[str, int] = field(default_factory=dict, repr=False)

    def can_dispatch(self, target: str, weight: str) -> bool:
        active = self._active_per_target.get(target, 0)
        if active >= self.max_concurrent_per_target:
            return False
        if weight == JobWeight.heavy:
            heavy_active = sum(
                1 for t, c in self._active_per_target.items() if c > 0 and t == target
            )
            if heavy_active >= self.heavy_job_limit:
                return False
        return True

    def acquire(self, target: str) -> None:
        self._active_per_target[target] = self._active_per_target.get(target, 0) + 1

    def release(self, target: str) -> None:
        current = self._active_per_target.get(target, 0)
        self._active_per_target[target] = max(0, current - 1)

    def backoff_seconds(self, attempt: int) -> float:
        if not self.enable_backoff:
            return 0.0
        delay = self.backoff_base_seconds * (2 ** (attempt - 1))
        return min(delay, self.backoff_max_seconds)


_settings = DispatcherSettings()


def get_settings() -> DispatcherSettings:
    return _settings


def configure_dispatcher(settings: DispatcherSettings) -> None:
    global _settings
    _settings = settings


# ---------------------------------------------------------------------------
# Source entity resolution
# ---------------------------------------------------------------------------


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

    if isinstance(
        entity,
        (AiRiskAssessment, Nis2ObligationRecord, Iso42001GapRecord, AiSystem),
    ):
        return mapper(entity)

    if hasattr(entity, "model_dump"):
        return mapper(entity.model_dump())
    if isinstance(entity, dict):
        return mapper(entity)
    return None


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def dispatch_one(
    job: IntegrationJob,
    *,
    settings: DispatcherSettings | None = None,
) -> bool:
    """Dispatch a single job.  Returns True on success."""
    cfg = settings or _settings

    if cfg.enable_backoff and job.attempt_count > 0:
        delay = cfg.backoff_seconds(job.attempt_count)
        if delay > 0:
            time.sleep(delay)

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
            _internal=True,
        )
        return False

    target_key = job.target.value
    if not cfg.can_dispatch(target_key, job.weight.value):
        logger.info(
            "integration_dispatch_throttled",
            extra={"job_id": job.job_id, "target": target_key},
        )
        return False

    cfg.acquire(target_key)
    try:
        connector = connector_for_target(target_key)
        update_job_status(
            job.job_id,
            IntegrationJobStatus.dispatched,
            _internal=True,
        )

        result = connector.dispatch(job, payload)
        if result.success:
            update_job_status(
                job.job_id,
                IntegrationJobStatus.delivered,
                dispatch_result=result.message,
                artifact_name=result.artifact_name,
                envelope_id=result.envelope_id,
                _internal=True,
            )
            return True

        if job.attempt_count >= MAX_DISPATCH_ATTEMPTS:
            update_job_status(
                job.job_id,
                IntegrationJobStatus.dead_letter,
                dispatch_result=result.message,
                _internal=True,
            )
        else:
            update_job_status(
                job.job_id,
                IntegrationJobStatus.failed,
                dispatch_result=result.message,
                _internal=True,
            )
        return False
    finally:
        cfg.release(target_key)


def dispatch_pending(
    *,
    settings: DispatcherSettings | None = None,
) -> dict[str, int]:
    """Process all pending jobs with priority ordering.

    Higher priority values are dispatched first.  Within the same
    priority, DATEV jobs get a configurable boost.
    """
    cfg = settings or _settings
    counts: dict[str, int] = {
        "dispatched": 0,
        "delivered": 0,
        "failed": 0,
        "dead_letter": 0,
        "throttled": 0,
    }
    jobs = pending_jobs(_internal=True)
    jobs.sort(
        key=lambda j: (
            j.priority + (cfg.datev_priority_boost if j.target == "datev_export" else 0),
            j.created_at,
        ),
        reverse=True,
    )

    for job in jobs:
        ok = dispatch_one(job, settings=cfg)
        if ok:
            counts["delivered"] += 1
        elif job.status == IntegrationJobStatus.pending:
            counts["throttled"] += 1
        elif job.status == IntegrationJobStatus.dead_letter:
            counts["dead_letter"] += 1
        else:
            counts["failed"] += 1
    return counts
