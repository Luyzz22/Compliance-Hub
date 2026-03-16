"""Export-Jobs für Board-Report (PDF-/DMS-Integration, Webhook, SAP BTP, DMS)."""

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
SAP_BTP_HTTP_HEADER = "X-ComplianceHub-Integration"
SAP_BTP_HTTP_HEADER_VALUE = "sap_btp_http"


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


def _post_with_headers(url: str, payload: dict, headers: dict[str, str]) -> tuple[bool, str]:
    """POST mit zusätzlichen Headern. Returns (success, error_message)."""
    try:
        with httpx.Client(timeout=WEBHOOK_TIMEOUT_SEC) as client:
            r = client.post(url, json=payload, headers=headers)
            if r.is_success:
                return True, ""
            return False, f"HTTP {r.status_code}"
    except httpx.TimeoutException:
        return False, "Timeout"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:200]


def _build_sap_btp_http_payload(
    job_id: str,
    tenant_id: str,
    created_at: datetime,
    report: AIBoardGovernanceReport,
    markdown: str,
) -> dict:
    """Stabiles Payload-Schema für SAP BTP HTTP-Inbound."""
    return {
        "tenant_id": tenant_id,
        "report_period": report.period,
        "markdown": markdown,
        "report_metadata": {
            "job_id": job_id,
            "generated_at": report.generated_at.isoformat()
            if hasattr(report.generated_at, "isoformat")
            else str(report.generated_at),
            "period": report.period,
        },
    }


def dispatch_board_report_export_job(
    job_id: str,
    tenant_id: str,
    created_at: datetime,
    report: AIBoardGovernanceReport,
    body: BoardReportExportJobCreate,
) -> tuple[ExportJobStatus, str | None]:
    """
    Führt den Export je nach target_system aus.
    Returns (status, error_message).
    - generic_webhook: HTTP POST auf callback_url (Payload: job, report, markdown).
    - sap_btp_http: HTTP POST mit Header X-ComplianceHub-Integration: sap_btp_http,
      Payload tenant_id, report_period, markdown, report_metadata.
    - dms_generic: Platzhalter → not_implemented.
    - sap_btp / sharepoint: Kein Aufruf → sent (Backward-Kompatibilität).
    """
    if body.target_system == "generic_webhook":
        if not body.callback_url:
            return "failed", "callback_url required for target_system generic_webhook"
        markdown = render_board_report_markdown(report)
        payload = {
            "job": {
                "id": job_id,
                "tenant_id": tenant_id,
                "created_at": created_at.isoformat(),
                "target_system": body.target_system,
            },
            "report": report.model_dump(mode="json"),
            "markdown": markdown,
        }
        ok, err = _post_webhook(body.callback_url, payload)
        return ("sent", None) if ok else ("failed", err)

    if body.target_system == "sap_btp_http":
        if not body.callback_url:
            return "failed", "callback_url required for target_system sap_btp_http"
        markdown = render_board_report_markdown(report)
        payload = _build_sap_btp_http_payload(job_id, tenant_id, created_at, report, markdown)
        headers = {SAP_BTP_HTTP_HEADER: SAP_BTP_HTTP_HEADER_VALUE}
        ok, err = _post_with_headers(body.callback_url, payload, headers)
        return ("sent", None) if ok else ("failed", err)

    if body.target_system == "dms_generic":
        return "not_implemented", "DMS integration not yet implemented"

    # sap_btp, sharepoint: kein HTTP-Call, Job als „gesendet“ markiert (Backward-Kompatibilität)
    return "sent", None


def run_export_job(
    tenant_id: str,
    report: AIBoardGovernanceReport,
    body: BoardReportExportJobCreate,
) -> BoardReportExportJob:
    """
    Erstellt Job, ruft Dispatch auf, setzt Status. Keine personenbezogenen Daten.
    """
    from app.datetime_compat import UTC

    now = datetime.now(UTC)
    job_id = str(uuid.uuid4())
    status, error_message = dispatch_board_report_export_job(job_id, tenant_id, now, report, body)
    completed_at = datetime.now(UTC)
    if status in ("sent", "failed", "not_implemented"):
        pass  # completed_at bereits gesetzt
    else:
        completed_at = None

    if status == "sent":
        logger.info("Export job %s completed target=%s", job_id, body.target_system)
    elif status == "failed":
        logger.warning(
            "Export job %s failed target=%s status_code=%s",
            job_id,
            body.target_system,
            error_message or "",
        )
    elif status == "not_implemented":
        logger.info(
            "Export job %s not_implemented target=%s",
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
