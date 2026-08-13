"""Credential lookup digests use a deployment-owned HMAC pepper."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.security import hash_api_key


def _pepper(path: Path, value: str) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o400)
    return path


def test_production_credential_digest_is_deterministic_and_pepper_bound(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first = _pepper(tmp_path / "pepper-one", "a" * 48)
    second = _pepper(tmp_path / "pepper-two", "b" * 48)
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("COMPLIANCEHUB_CREDENTIAL_PEPPER_FILE", str(first))

    digest = hash_api_key("ch_example-opaque-credential")
    assert digest == hash_api_key("ch_example-opaque-credential")
    assert len(digest) == 64

    monkeypatch.setenv("COMPLIANCEHUB_CREDENTIAL_PEPPER_FILE", str(second))
    assert hash_api_key("ch_example-opaque-credential") != digest


def test_production_credential_digest_fails_closed_without_pepper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.delenv("COMPLIANCEHUB_CREDENTIAL_PEPPER", raising=False)
    monkeypatch.delenv("COMPLIANCEHUB_CREDENTIAL_PEPPER_FILE", raising=False)

    with pytest.raises(RuntimeError, match="CREDENTIAL_PEPPER_FILE is required"):
        hash_api_key("ch_example-opaque-credential")
