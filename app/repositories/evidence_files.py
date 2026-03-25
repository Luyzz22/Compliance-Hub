from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.evidence_models import EvidenceFile
from app.models_db import EvidenceFileTable


class EvidenceFileRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: EvidenceFileTable) -> EvidenceFile:
        return EvidenceFile(
            id=row.id,
            tenant_id=row.tenant_id,
            ai_system_id=row.ai_system_id,
            audit_record_id=row.audit_record_id,
            action_id=row.action_id,
            filename_original=row.filename_original,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
            uploaded_by=row.uploaded_by,
            norm_framework=row.norm_framework,
            norm_reference=row.norm_reference,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create(
        self,
        *,
        tenant_id: str,
        storage_key: str,
        filename_original: str,
        content_type: str,
        size_bytes: int,
        uploaded_by: str,
        ai_system_id: str | None,
        audit_record_id: str | None,
        action_id: str | None,
        norm_framework: str | None,
        norm_reference: str | None,
    ) -> EvidenceFile:
        now = datetime.now(UTC)
        eid = str(uuid4())
        row = EvidenceFileTable(
            id=eid,
            tenant_id=tenant_id,
            ai_system_id=ai_system_id,
            audit_record_id=audit_record_id,
            action_id=action_id,
            filename_original=filename_original,
            storage_key=storage_key,
            content_type=content_type,
            size_bytes=size_bytes,
            uploaded_by=uploaded_by,
            norm_framework=norm_framework,
            norm_reference=norm_reference,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_domain(row)

    def get_by_id(self, tenant_id: str, evidence_id: str) -> EvidenceFile | None:
        stmt = select(EvidenceFileTable).where(
            EvidenceFileTable.tenant_id == tenant_id,
            EvidenceFileTable.id == evidence_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row)

    def get_row_for_delete(self, tenant_id: str, evidence_id: str) -> EvidenceFileTable | None:
        stmt = select(EvidenceFileTable).where(
            EvidenceFileTable.tenant_id == tenant_id,
            EvidenceFileTable.id == evidence_id,
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def list_for_tenant(
        self,
        tenant_id: str,
        *,
        ai_system_id: str | None = None,
        audit_record_id: str | None = None,
        action_id: str | None = None,
    ) -> list[EvidenceFile]:
        stmt = select(EvidenceFileTable).where(EvidenceFileTable.tenant_id == tenant_id)
        if ai_system_id is not None:
            stmt = stmt.where(EvidenceFileTable.ai_system_id == ai_system_id)
        if audit_record_id is not None:
            stmt = stmt.where(EvidenceFileTable.audit_record_id == audit_record_id)
        if action_id is not None:
            stmt = stmt.where(EvidenceFileTable.action_id == action_id)
        stmt = stmt.order_by(EvidenceFileTable.created_at.desc())
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_domain(r) for r in rows]

    def delete(self, tenant_id: str, evidence_id: str) -> str | None:
        row = self.get_row_for_delete(tenant_id, evidence_id)
        if row is None:
            return None
        storage_key = row.storage_key
        self._session.delete(row)
        self._session.commit()
        return storage_key
