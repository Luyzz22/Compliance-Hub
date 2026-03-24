"""In-Memory KPI-Export-Jobs (Audit-Verknüpfung, ohne externen Versand)."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.ai_governance_models import (
    BoardKpiExportJob,
    BoardKpiExportJobCreate,
)
from app.datetime_compat import UTC

_jobs: dict[str, BoardKpiExportJob] = {}


def store_kpi_job(job: BoardKpiExportJob) -> None:
    _jobs[job.id] = job


def get_kpi_job(job_id: str, tenant_id: str) -> BoardKpiExportJob | None:
    job = _jobs.get(job_id)
    if job is None or job.tenant_id != tenant_id:
        return None
    return job


def register_kpi_export_job(
    tenant_id: str,
    body: BoardKpiExportJobCreate,
) -> BoardKpiExportJob:
    now = datetime.now(UTC)
    job = BoardKpiExportJob(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        created_at=now,
        completed_at=now,
        status="completed",
        target_system_label=body.target_system_label,
        export_format=body.export_format,
        metadata=body.metadata,
        error_message=None,
    )
    store_kpi_job(job)
    return job
