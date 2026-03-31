"""In-memory integration job store with outbox creation.

Thread-safe, idempotent job creation based on idempotency_key.
Designed as a thin layer swappable for a database later.
"""

from __future__ import annotations

import logging
from threading import Lock
from typing import Any

from app.integrations.models import (
    IntegrationJob,
    IntegrationJobStatus,
    _now_iso,
)
from app.services.rag.evidence_store import record_event

logger = logging.getLogger(__name__)

_lock = Lock()
_jobs: dict[str, IntegrationJob] = {}
_idem_index: dict[str, str] = {}

ENABLED_PAYLOAD_TYPES: set[str] = set()


def configure_enabled_types(types: set[str]) -> None:
    """Opt-in feature flag: only these payload types create outbox jobs."""
    ENABLED_PAYLOAD_TYPES.clear()
    ENABLED_PAYLOAD_TYPES.update(types)


def enqueue_job(job: IntegrationJob) -> IntegrationJob | None:
    """Create an integration job (outbox entry).

    Returns None if the payload_type is not enabled or the job is a
    duplicate (same idempotency_key).
    """
    if ENABLED_PAYLOAD_TYPES and job.payload_type.value not in ENABLED_PAYLOAD_TYPES:
        return None

    key = job.idempotency_key
    with _lock:
        if key and key in _idem_index:
            existing_id = _idem_index[key]
            if existing_id in _jobs:
                logger.info(
                    "integration_job_duplicate",
                    extra={"key": key, "existing": existing_id},
                )
                return _jobs[existing_id]
        _jobs[job.job_id] = job
        if key:
            _idem_index[key] = job.job_id

    _log_event("integration_job_created", job)
    return job


def get_job(job_id: str) -> IntegrationJob | None:
    with _lock:
        return _jobs.get(job_id)


def list_jobs(
    *,
    tenant_id: str | None = None,
    client_id: str | None = None,
    status: str | None = None,
    target: str | None = None,
    payload_type: str | None = None,
) -> list[IntegrationJob]:
    with _lock:
        out = list(_jobs.values())
    if tenant_id:
        out = [j for j in out if j.tenant_id == tenant_id]
    if client_id:
        out = [j for j in out if j.client_id == client_id]
    if status:
        out = [j for j in out if j.status == status]
    if target:
        out = [j for j in out if j.target == target]
    if payload_type:
        out = [j for j in out if j.payload_type == payload_type]
    return out


def update_job_status(
    job_id: str,
    new_status: IntegrationJobStatus,
    *,
    dispatch_result: str = "",
) -> IntegrationJob | None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        job.status = new_status
        job.last_attempt_at = _now_iso()
        if dispatch_result:
            job.last_dispatch_result = dispatch_result
        if new_status in (
            IntegrationJobStatus.dispatched,
            IntegrationJobStatus.failed,
        ):
            job.attempt_count += 1
    _log_event(f"integration_job_{new_status.value}", job)
    return job


def mark_for_retry(job_id: str) -> IntegrationJob | None:
    """Reset a failed job to pending for retry."""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        if job.status not in (
            IntegrationJobStatus.failed,
            IntegrationJobStatus.dead_letter,
        ):
            return None
        job.status = IntegrationJobStatus.pending
        job.last_dispatch_result = ""
    _log_event("integration_job_retried", job)
    return job


def pending_jobs() -> list[IntegrationJob]:
    with _lock:
        return [j for j in _jobs.values() if j.status == IntegrationJobStatus.pending]


def clear_for_tests() -> None:
    with _lock:
        _jobs.clear()
        _idem_index.clear()
    ENABLED_PAYLOAD_TYPES.clear()


def _log_event(event_type: str, job: IntegrationJob) -> None:
    payload: dict[str, Any] = {
        "event_type": event_type,
        "job_id": job.job_id,
        "tenant_id": job.tenant_id,
        "client_id": job.client_id,
        "system_id": job.system_id,
        "target": job.target.value,
        "payload_type": job.payload_type.value,
        "source_entity_type": job.source_entity_type,
        "source_entity_id": job.source_entity_id,
        "status": job.status.value,
        "attempt_count": job.attempt_count,
        "trace_id": job.trace_id,
    }
    record_event(payload)
    logger.info(event_type, extra=payload)
