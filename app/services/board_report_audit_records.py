"""Audit-Ready: Board-Report-Audit-Records (Versionierung, verknüpfte Export-Jobs)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

from app.ai_governance_models import (
    AIBoardGovernanceReport,
    BoardReportAuditRecord,
    BoardReportAuditRecordCreate,
)

_records: dict[str, BoardReportAuditRecord] = {}


def _report_version(report: AIBoardGovernanceReport) -> str:
    """Deterministischer Version-String aus Report-Inhalt (Hash)."""
    raw = json.dumps(report.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def store_record(record: BoardReportAuditRecord) -> None:
    _records[record.id] = record


def create_audit_record(
    tenant_id: str,
    report: AIBoardGovernanceReport,
    body: BoardReportAuditRecordCreate,
    created_by: str,
) -> BoardReportAuditRecord:
    """Legt einen neuen Audit-Record an (Report-Version = Hash des JSON)."""
    from app.datetime_compat import UTC

    now = datetime.now(UTC)
    record_id = str(uuid.uuid4())
    report_version = _report_version(report)
    gen_at = report.generated_at
    record = BoardReportAuditRecord(
        id=record_id,
        tenant_id=tenant_id,
        report_generated_at=gen_at,
        report_version=report_version,
        created_at=now,
        created_by=created_by,
        purpose=body.purpose,
        linked_export_job_ids=body.linked_export_job_ids or [],
        linked_kpi_export_job_ids=body.linked_kpi_export_job_ids or [],
        status=body.status,
    )
    store_record(record)
    return record


def get_record(record_id: str, tenant_id: str) -> BoardReportAuditRecord | None:
    r = _records.get(record_id)
    if r is None or r.tenant_id != tenant_id:
        return None
    return r


def list_records(
    tenant_id: str,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[BoardReportAuditRecord]:
    """Listet Audit-Records des Tenants (gefiltert nach status, paginiert)."""
    out = [r for r in _records.values() if r.tenant_id == tenant_id]
    if status is not None:
        out = [r for r in out if r.status == status]
    out.sort(key=lambda r: r.created_at, reverse=True)
    return out[offset : offset + limit]
