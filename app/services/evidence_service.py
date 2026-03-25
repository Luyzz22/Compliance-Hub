from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.evidence_models import EvidenceFile
from app.repositories.ai_governance_actions import AIGovernanceActionRepository
from app.repositories.ai_systems import AISystemRepository
from app.repositories.evidence_files import EvidenceFileRepository
from app.services.board_report_audit_records import get_record
from app.services.evidence_storage import EvidenceStorageBackend

logger = logging.getLogger(__name__)

DEFAULT_MAX_BYTES = 20 * 1024 * 1024

ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "image/png",
        "image/jpeg",
    }
)

EXT_TO_CT: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def _max_bytes() -> int:
    raw = os.getenv("EVIDENCE_MAX_BYTES", str(DEFAULT_MAX_BYTES))
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_BYTES


def sanitize_original_filename(name: str) -> str:
    base = Path(name).name.replace("\x00", "")
    base = base.strip() or "upload.bin"
    return base[:512]


def resolve_content_type(declared: str | None, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if declared:
        base = declared.split(";")[0].strip().lower()
        if base in {c.lower() for c in ALLOWED_CONTENT_TYPES}:
            return declared.split(";")[0].strip()
    return EXT_TO_CT.get(ext, "")


def validate_content_type(content_type: str) -> None:
    if content_type.lower() not in {c.lower() for c in ALLOWED_CONTENT_TYPES}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {content_type}",
        )


def _validate_single_parent(
    ai_system_id: str | None,
    audit_record_id: str | None,
    action_id: str | None,
) -> None:
    n = sum(1 for x in (ai_system_id, audit_record_id, action_id) if x)
    if n != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of ai_system_id, audit_record_id, action_id must be provided",
        )


def _validate_references(
    tenant_id: str,
    ai_system_id: str | None,
    audit_record_id: str | None,
    action_id: str | None,
    *,
    ai_repo: AISystemRepository,
    action_repo: AIGovernanceActionRepository,
) -> None:
    if ai_system_id:
        if ai_repo.get_by_id(tenant_id, ai_system_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ai_system_id not found for this tenant",
            )
    if audit_record_id:
        if get_record(audit_record_id, tenant_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="audit_record_id not found for this tenant",
            )
    if action_id:
        if action_repo.get(tenant_id, action_id) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="action_id not found for this tenant",
            )


async def upload_evidence(
    *,
    tenant_id: str,
    uploaded_by: str,
    file: UploadFile,
    ai_system_id: str | None,
    audit_record_id: str | None,
    action_id: str | None,
    norm_framework: str | None,
    norm_reference: str | None,
    evidence_repo: EvidenceFileRepository,
    storage: EvidenceStorageBackend,
    ai_repo: AISystemRepository,
    action_repo: AIGovernanceActionRepository,
) -> EvidenceFile:
    _validate_single_parent(ai_system_id, audit_record_id, action_id)
    _validate_references(
        tenant_id,
        ai_system_id,
        audit_record_id,
        action_id,
        ai_repo=ai_repo,
        action_repo=action_repo,
    )

    raw_name = file.filename or "upload.bin"
    filename_original = sanitize_original_filename(raw_name)
    content_type = resolve_content_type(file.content_type, filename_original)
    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine allowed file type from content type or extension",
        )
    validate_content_type(content_type)

    data = await file.read()
    max_b = _max_bytes()
    if len(data) > max_b:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_b} bytes",
        )
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file",
        )

    nf = (norm_framework or "").strip()[:64] or None
    nr = (norm_reference or "").strip()[:256] or None

    storage_key = storage.store_file(tenant_id, data, content_type)
    try:
        created = evidence_repo.create(
            tenant_id=tenant_id,
            storage_key=storage_key,
            filename_original=filename_original,
            content_type=content_type,
            size_bytes=len(data),
            uploaded_by=uploaded_by,
            ai_system_id=ai_system_id,
            audit_record_id=audit_record_id,
            action_id=action_id,
            norm_framework=nf,
            norm_reference=nr,
        )
    except Exception:
        storage.delete_file(tenant_id, storage_key)
        raise

    logger.info(
        "evidence_upload tenant=%s evidence_id=%s parent=%s size=%s ct=%s",
        tenant_id,
        created.id,
        (
            f"ai_system={ai_system_id}"
            if ai_system_id
            else f"audit={audit_record_id}"
            if audit_record_id
            else f"action={action_id}"
        ),
        len(data),
        content_type,
    )
    return created


def list_evidence(
    tenant_id: str,
    *,
    ai_system_id: str | None,
    audit_record_id: str | None,
    action_id: str | None,
    evidence_repo: EvidenceFileRepository,
) -> list[EvidenceFile]:
    if sum(1 for x in (ai_system_id, audit_record_id, action_id) if x) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one filter: ai_system_id, audit_record_id, or action_id",
        )
    return evidence_repo.list_for_tenant(
        tenant_id,
        ai_system_id=ai_system_id,
        audit_record_id=audit_record_id,
        action_id=action_id,
    )


def download_evidence(
    tenant_id: str,
    evidence_id: str,
    *,
    evidence_repo: EvidenceFileRepository,
    storage: EvidenceStorageBackend,
) -> tuple[bytes, str, str]:
    db_row = evidence_repo.get_row_for_delete(tenant_id, evidence_id)
    if db_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    try:
        blob = storage.retrieve_file(tenant_id, db_row.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidence file missing on storage",
        ) from None
    return blob, db_row.content_type, db_row.filename_original


def delete_evidence(
    tenant_id: str,
    evidence_id: str,
    *,
    evidence_repo: EvidenceFileRepository,
    storage: EvidenceStorageBackend,
) -> None:
    storage_key = evidence_repo.delete(tenant_id, evidence_id)
    if storage_key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    try:
        storage.delete_file(tenant_id, storage_key)
    except Exception:
        logger.exception(
            "evidence_delete_storage_failed tenant=%s evidence_id=%s key=%s",
            tenant_id,
            evidence_id,
            storage_key,
        )
    logger.info("evidence_delete tenant=%s evidence_id=%s", tenant_id, evidence_id)
