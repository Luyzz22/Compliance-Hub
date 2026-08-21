from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from uuid import uuid4

import httpx

from app.secret_files import production_runtime, read_secret

logger = logging.getLogger(__name__)

_MAX_EVIDENCE_BYTES = 32 * 1024 * 1024
_S3_BUCKET_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{1,61}[a-z0-9])?$")
_S3_REGION_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
_S3_PREFIX_RE = re.compile(r"^[a-z0-9](?:[a-z0-9/_-]{0,126}[a-z0-9])?$")
_HETZNER_S3_HOSTS = {"fsn1.your-objectstorage.com", "nbg1.your-objectstorage.com"}


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


def _required_environment(name: str, environment: Mapping[str, str]) -> str:
    value = environment.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required for S3 evidence storage")
    return value


class S3EvidenceStorage:
    """Tenant-scoped S3 evidence storage using bounded synchronous SigV4 requests."""

    def __init__(
        self,
        *,
        environment: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        env = environment or os.environ
        endpoint = urlsplit(_required_environment("COMPLIANCEHUB_S3_ENDPOINT", env))
        if (
            endpoint.scheme != "https"
            or not endpoint.hostname
            or endpoint.username
            or endpoint.password
            or endpoint.path not in {"", "/"}
            or endpoint.query
            or endpoint.fragment
        ):
            raise RuntimeError("COMPLIANCEHUB_S3_ENDPOINT must be a bare HTTPS origin")
        configured_hosts = {
            host.strip().lower()
            for host in env.get("COMPLIANCEHUB_S3_ALLOWED_HOSTS", "").split(",")
            if host.strip()
        }
        allowed_hosts = _HETZNER_S3_HOSTS | configured_hosts
        if endpoint.hostname.lower() not in allowed_hosts:
            raise RuntimeError("S3 evidence endpoint host is not in the allowlist")

        bucket = _required_environment("COMPLIANCEHUB_S3_BUCKET", env).lower()
        if not _S3_BUCKET_RE.fullmatch(bucket) or ".." in bucket:
            raise RuntimeError("COMPLIANCEHUB_S3_BUCKET is invalid")
        region = _required_environment("COMPLIANCEHUB_S3_REGION", env).lower()
        if not _S3_REGION_RE.fullmatch(region):
            raise RuntimeError("COMPLIANCEHUB_S3_REGION is invalid")
        prefix = env.get("COMPLIANCEHUB_EVIDENCE_STORAGE_PREFIX", "compliancehub/evidence/v1")
        prefix = prefix.strip().lower().strip("/")
        if not _S3_PREFIX_RE.fullmatch(prefix) or ".." in prefix or "//" in prefix:
            raise RuntimeError("COMPLIANCEHUB_EVIDENCE_STORAGE_PREFIX is invalid")

        self._endpoint = endpoint
        self._bucket = bucket
        self._region = region
        self._prefix = prefix
        self._force_path_style = env.get("COMPLIANCEHUB_S3_FORCE_PATH_STYLE", "false").lower() == (
            "true"
        )
        self._access_key = read_secret(
            "COMPLIANCEHUB_S3_ACCESS_KEY",
            "COMPLIANCEHUB_S3_ACCESS_KEY_FILE",
            required=True,
            minimum_characters=16,
        )
        self._secret_key = read_secret(
            "COMPLIANCEHUB_S3_SECRET_ACCESS_KEY",
            "COMPLIANCEHUB_S3_SECRET_ACCESS_KEY_FILE",
            required=True,
            minimum_characters=32,
        )
        if any(character in self._access_key + self._secret_key for character in "\r\n\x00"):
            raise RuntimeError("S3 evidence credentials contain control characters")
        self._transport = transport
        self._now = now or (lambda: datetime.now(UTC))

    def _object_key(self, storage_key: str) -> str:
        return f"{self._prefix}/{storage_key}"

    def _signed_request(
        self,
        method: str,
        storage_key: str,
        *,
        content: bytes = b"",
        content_type: str | None = None,
    ) -> httpx.Response:
        object_key = self._object_key(storage_key)
        canonical_object_path = quote(object_key, safe="/-_.~")
        endpoint_host = (self._endpoint.hostname or "").lower()
        port = self._endpoint.port
        if self._force_path_style:
            host = endpoint_host
            canonical_uri = f"/{quote(self._bucket, safe='-_.~')}/{canonical_object_path}"
        else:
            host = f"{self._bucket}.{endpoint_host}"
            canonical_uri = f"/{canonical_object_path}"
        host_header = f"{host}:{port}" if port and port != 443 else host
        netloc = host_header
        url = urlunsplit((self._endpoint.scheme, netloc, canonical_uri, "", ""))

        instant = self._now().astimezone(UTC)
        amz_date = instant.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = instant.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(content).hexdigest()
        canonical_headers = (
            f"host:{host_header}\nx-amz-content-sha256:{payload_hash}\nx-amz-date:{amz_date}\n"
        )
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        canonical_request = "\n".join(
            (method, canonical_uri, "", canonical_headers, signed_headers, payload_hash)
        )
        scope = f"{date_stamp}/{self._region}/s3/aws4_request"
        string_to_sign = "\n".join(
            (
                "AWS4-HMAC-SHA256",
                amz_date,
                scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            )
        )
        date_key = hmac.new(
            f"AWS4{self._secret_key}".encode(), date_stamp.encode(), hashlib.sha256
        ).digest()
        region_key = hmac.new(date_key, self._region.encode(), hashlib.sha256).digest()
        service_key = hmac.new(region_key, b"s3", hashlib.sha256).digest()
        signing_key = hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
        headers = {
            "Authorization": (
                f"AWS4-HMAC-SHA256 Credential={self._access_key}/{scope}, "
                f"SignedHeaders={signed_headers}, Signature={signature}"
            ),
            "Host": host_header,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if content_type:
            headers["Content-Type"] = content_type
        try:
            with httpx.Client(
                transport=self._transport,
                timeout=httpx.Timeout(15.0),
                follow_redirects=False,
                trust_env=False,
            ) as client:
                return client.request(method, url, headers=headers, content=content)
        except httpx.HTTPError as error:
            raise RuntimeError(f"S3 evidence {method.lower()} request failed") from error

    def store_file(self, tenant_id: str, data: bytes, content_type: str) -> str:
        if len(data) > _MAX_EVIDENCE_BYTES:
            raise ValueError("Evidence object exceeds the maximum size")
        storage_key = f"{_tenant_path_segment(tenant_id)}/{uuid4()}"
        response = self._signed_request("PUT", storage_key, content=data, content_type=content_type)
        if response.status_code not in {200, 201}:
            raise RuntimeError("S3 evidence put was rejected")
        return storage_key

    def retrieve_file(self, tenant_id: str, storage_key: str) -> bytes:
        _validate_storage_key(tenant_id, storage_key)
        response = self._signed_request("GET", storage_key)
        if response.status_code == 404:
            raise FileNotFoundError(storage_key)
        if response.status_code != 200:
            raise RuntimeError("S3 evidence get was rejected")
        if len(response.content) > _MAX_EVIDENCE_BYTES:
            raise RuntimeError("S3 evidence object exceeds the maximum size")
        return response.content

    def delete_file(self, tenant_id: str, storage_key: str) -> None:
        _validate_storage_key(tenant_id, storage_key)
        response = self._signed_request("DELETE", storage_key)
        if response.status_code not in {200, 204}:
            raise RuntimeError("S3 evidence delete was rejected")


def get_evidence_storage() -> EvidenceStorageBackend:
    backend = (
        os.getenv(
            "COMPLIANCEHUB_EVIDENCE_STORAGE_BACKEND",
            os.getenv("COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND", "local"),
        )
        .strip()
        .lower()
    )
    if backend == "s3":
        return S3EvidenceStorage()
    if backend == "local":
        if production_runtime():
            raise RuntimeError("Local evidence storage is forbidden in production")
        return LocalFilesystemEvidenceStorage()
    raise RuntimeError("Unsupported evidence storage backend")
