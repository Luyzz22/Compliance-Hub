from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from app.services.evidence_storage import S3EvidenceStorage, get_evidence_storage


def _environment() -> dict[str, str]:
    return {
        "COMPLIANCEHUB_S3_ENDPOINT": "https://nbg1.your-objectstorage.com",
        "COMPLIANCEHUB_S3_ALLOWED_HOSTS": "nbg1.your-objectstorage.com",
        "COMPLIANCEHUB_S3_REGION": "nbg1",
        "COMPLIANCEHUB_S3_BUCKET": "compliancehub-synthetic-test",
        "COMPLIANCEHUB_S3_FORCE_PATH_STYLE": "false",
        "COMPLIANCEHUB_EVIDENCE_STORAGE_PREFIX": "compliancehub/evidence/v1",
    }


def test_s3_evidence_storage_signs_tenant_scoped_put_get_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "test")
    monkeypatch.setenv("COMPLIANCEHUB_S3_ACCESS_KEY", "SYNTHETICACCESS1")
    monkeypatch.setenv("COMPLIANCEHUB_S3_SECRET_ACCESS_KEY", "s" * 40)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, content=b"synthetic evidence")
        return httpx.Response(204 if request.method == "DELETE" else 200)

    storage = S3EvidenceStorage(
        environment=_environment(),
        transport=httpx.MockTransport(handler),
        now=lambda: datetime(2026, 8, 21, 1, 2, 3, tzinfo=UTC),
    )
    storage_key = storage.store_file("tenant/a", b"synthetic evidence", "text/plain")
    assert storage.retrieve_file("tenant/a", storage_key) == b"synthetic evidence"
    storage.delete_file("tenant/a", storage_key)

    assert [request.method for request in requests] == ["PUT", "GET", "DELETE"]
    for request in requests:
        assert request.url.host == "compliancehub-synthetic-test.nbg1.your-objectstorage.com"
        assert request.url.path.startswith("/compliancehub/evidence/v1/tenant%2Fa/")
        assert request.headers["authorization"].startswith(
            "AWS4-HMAC-SHA256 Credential=SYNTHETICACCESS1/20260821/nbg1/s3/aws4_request"
        )
        assert request.headers["x-amz-date"] == "20260821T010203Z"
        assert len(request.headers["x-amz-content-sha256"]) == 64


def test_s3_evidence_storage_rejects_cross_tenant_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "test")
    monkeypatch.setenv("COMPLIANCEHUB_S3_ACCESS_KEY", "SYNTHETICACCESS1")
    monkeypatch.setenv("COMPLIANCEHUB_S3_SECRET_ACCESS_KEY", "s" * 40)
    storage = S3EvidenceStorage(
        environment=_environment(),
        transport=httpx.MockTransport(lambda _request: httpx.Response(500)),
    )
    with pytest.raises(ValueError, match="does not match tenant"):
        storage.retrieve_file("tenant-b", "tenant-a/object")


def test_evidence_storage_factory_forbids_local_backend_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("COMPLIANCEHUB_EVIDENCE_STORAGE_BACKEND", "local")
    with pytest.raises(RuntimeError, match="forbidden in production"):
        get_evidence_storage()
