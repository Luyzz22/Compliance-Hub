"""Export-Jobs für Board-Report (PDF-/DMS-Integration, generischer Webhook)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

import httpx

from app.ai_governance_models import (
    AIBoardGovernanceReport,
    BoardReportExportJob,
    BoardReportExportJobCreate,
    ExportJobStatus,
)
from app.services.board_report_markdown import render_board_report_markdown

logger = logging.getLogger(__name__)

# In-memory Store (Tenant-isoliert, nur Job-Metadaten)
_jobs: dict[str, BoardReportExportJob] = {}

WEBHOOK_TIMEOUT_SEC = 10.0


def store_job(job: BoardReportExportJob) -> None:
    _jobs[job.id] = job


def get_job(job_id: str, tenant_id: str) -> BoardReportExportJob | None:
    job = _jobs.get(job_id)
    if job is None or job.tenant_id != tenant_id:
        return None
    return job


def _post_webhook(url: str, payload: dict) -> tuple[bool, str]:
    """Sendet Payload per POST an url. Returns (success, error_message)."""
    try:
        with httpx.Client(timeout=WEBHOOK_TIMEOUT_SEC) as client:
            r = client.post(url, json=payload)
            if r.is_success:
                return True, ""
            return False, f"HTTP {r.status_code}"
    except httpx.TimeoutException:
        return False, "Timeout"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]


def run_export_job(
    tenant_id: str,
    report: AIBoardGovernanceReport,
    body: BoardReportExportJobCreate,
) -> BoardReportExportJob:
    """
    Erstellt Job, optional Webhook-POST, speichert Job. Keine personenbezogenen Daten.
    """
    from app.datetime_compat import UTC

    now = datetime.now(UTC)
    job_id = str(uuid.uuid4())
    status: ExportJobStatus = "pending"
    error_message: str | None = None
    completed_at: datetime | None = None

    if body.target_system == "generic_webhook" and body.callback_url:
        markdown = render_board_report_markdown(report)
        payload = {
            "job": {
                "id": job_id,
                "tenant_id": tenant_id,
                "created_at": now.isoformat(),
                "target_system": body.target_system,
            },
            "report": report.model_dump(mode="json"),
            "markdown": markdown,
        }
        ok, err = _post_webhook(body.callback_url, payload)
        completed_at = datetime.now(UTC)
        if ok:
            status = "sent"
            logger.info(
                "Export job %s webhook sent target=%s",
                job_id,
                body.target_system,
            )
        else:
            status = "failed"
            error_message = err
            logger.warning(
                "Export job %s webhook failed target=%s error=%s",
                job_id,
                body.target_system,
                err,
            )
    else:
        status = "sent"
        completed_at = now
        logger.info(
            "Export job %s created (no webhook) target=%s",
            job_id,
            body.target_system,
        )

    job = BoardReportExportJob(
        id=job_id,
        tenant_id=tenant_id,
        created_at=now,
        status=status,
        target_system=body.target_system,
        callback_url=body.callback_url,
        metadata=body.metadata,
        error_message=error_message,
        completed_at=completed_at,
    )
    store_job(job)
    return job
