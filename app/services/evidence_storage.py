from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, unquote
from uuid import uuid4

logger = logging.getLogger(__name__)


class EvidenceStorageBackend(Protocol):
    """Austauschbar gegen S3/Blob; API bleibt tenant-bewusst."""

    def store_file(self, tenant_id: str, data: bytes, content_type: str) -> str:
        """Persistiert Bytes; liefert internen storage_key (relativ zum Root)."""
        ...

    def retrieve_file(self, tenant_id: str, storage_key: str) -> bytes: ...

    def delete_file(self, tenant_id: str, storage_key: str) -> None: ...


def _tenant_path_segment(tenant_id: str) -> str:
    return quote(tenant_id, safe="")


def _validate_storage_key(tenant_id: str, storage_key: str) -> None:
    if ".." in storage_key or storage_key.startswith("/"):
        raise ValueError("Invalid storage key")
    parts = storage_key.split("/", 1)
    if len(parts) != 2:
        raise ValueError("Invalid storage key shape")
    if unquote(parts[0]) != tenant_id:
        raise ValueError("Storage key does not match tenant")


class LocalFilesystemEvidenceStorage:
    """Ablage unter EVIDENCE_STORAGE_PATH / {tenant_id} / {uuid} (ohne Original-Dateinamen)."""

    def __init__(self, root: Path | None = None) -> None:
        raw = os.getenv("EVIDENCE_STORAGE_PATH", "./data/evidence")
        self._root = Path(root) if root is not None else Path(raw).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _abs_path(self, tenant_id: str, storage_key: str) -> Path:
        _validate_storage_key(tenant_id, storage_key)
        return self._root / storage_key

    def store_file(self, tenant_id: str, data: bytes, content_type: str) -> str:
        _ = content_type
        td = _tenant_path_segment(tenant_id)
        file_id = str(uuid4())
        rel = f"{td}/{file_id}"
        dest_dir = self._root / td
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / file_id
        dest_file.write_bytes(data)
        logger.debug("Evidence stored: key=%s size=%s", rel, len(data))
        return rel

    def retrieve_file(self, tenant_id: str, storage_key: str) -> bytes:
        path = self._abs_path(tenant_id, storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return path.read_bytes()

    def delete_file(self, tenant_id: str, storage_key: str) -> None:
        path = self._abs_path(tenant_id, storage_key)
        if path.is_file():
            path.unlink()
            logger.debug("Evidence file removed: key=%s", storage_key)


def get_evidence_storage() -> EvidenceStorageBackend:
    return LocalFilesystemEvidenceStorage()
