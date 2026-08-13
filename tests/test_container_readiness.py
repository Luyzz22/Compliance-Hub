"""Container readiness probe keeps the monitoring credential out of argv."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import container_readiness


def _secret(tmp_path: Path, value: str = "r" * 48) -> Path:
    path = tmp_path / "health-key"
    path.write_text(value, encoding="utf-8")
    path.chmod(0o400)
    return path


def test_probe_reads_a_hardened_secret_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secret = _secret(tmp_path)
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY_FILE", str(secret))
    monkeypatch.setenv("COMPLIANCEHUB_PUBLIC_HOST", "app.complywithai.de")

    assert container_readiness._read_health_key() == "r" * 48


def test_probe_rejects_relative_weak_or_short_secret_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY_FILE", "relative-key")
    with pytest.raises(RuntimeError, match="absolute"):
        container_readiness._read_health_key()

    secret = _secret(tmp_path)
    secret.chmod(0o644)
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY_FILE", str(secret))
    with pytest.raises(RuntimeError, match="mode"):
        container_readiness._read_health_key()

    short = _secret(tmp_path, "short")
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY_FILE", str(short))
    with pytest.raises(RuntimeError, match="at least 32"):
        container_readiness._read_health_key()


def test_probe_sends_key_as_header_and_requires_ready_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secret = _secret(tmp_path)
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY_FILE", str(secret))
    monkeypatch.setenv("COMPLIANCEHUB_PUBLIC_HOST", "app.complywithai.de")
    observed: dict[str, object] = {}

    class Response:
        status = 200

        def read(self, _amount: int) -> bytes:
            return b'{"app":"up","db":"up","policy_engine":"up","external_ai_provider":"up"}'

    class Connection:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            observed["origin"] = f"http://{host}:{port}"
            observed["timeout"] = timeout

        def request(self, method: str, path: str, headers: dict[str, str]) -> None:
            observed["method"] = method
            observed["path"] = path
            observed["key"] = headers["X-HEALTH-KEY"]
            observed["host"] = headers["Host"]

        def getresponse(self) -> Response:
            return Response()

        def close(self) -> None:
            observed["closed"] = True

    monkeypatch.setattr(container_readiness.http.client, "HTTPConnection", Connection)

    assert container_readiness.main() == 0
    assert observed == {
        "origin": "http://127.0.0.1:8000",
        "method": "GET",
        "path": "/api/internal/readiness",
        "key": "r" * 48,
        "host": "app.complywithai.de",
        "timeout": 3,
        "closed": True,
    }


def test_probe_fails_closed_without_a_safe_trusted_host(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    secret = _secret(tmp_path)
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY_FILE", str(secret))
    monkeypatch.setenv("COMPLIANCEHUB_PUBLIC_HOST", "https://unsafe.example")

    assert container_readiness.main() == 1
