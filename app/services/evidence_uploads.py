from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

from app.evidence_upload_models import EvidenceUploadMetadata, EvidenceUploadRegisterRequest


class EvidenceUploadService:
    """In-Memory-Platzhalter: später durch DB-Repository + S3/Blob ersetzen."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_id: dict[str, EvidenceUploadMetadata] = {}
        self._by_tenant: dict[str, list[str]] = {}

    def register(
        self,
        tenant_id: str,
        body: EvidenceUploadRegisterRequest,
    ) -> EvidenceUploadMetadata:
        now = datetime.now(UTC)
        eid = str(uuid4())
        meta = EvidenceUploadMetadata(
            id=eid,
            tenant_id=tenant_id,
            ai_system_id=body.ai_system_id,
            related_action_id=body.related_action_id,
            filename=body.filename,
            content_type=body.content_type,
            size=body.size,
            created_at=now,
        )
        with self._lock:
            self._by_id[eid] = meta
            self._by_tenant.setdefault(tenant_id, []).append(eid)
        return meta

    def list_for_tenant(self, tenant_id: str) -> list[EvidenceUploadMetadata]:
        with self._lock:
            ids = list(self._by_tenant.get(tenant_id, ()))
        return [self._by_id[i] for i in ids if i in self._by_id]


evidence_upload_service = EvidenceUploadService()
