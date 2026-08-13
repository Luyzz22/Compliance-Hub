from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.secret_files import read_secret


def _write_secret(path: Path, value: str, mode: int = 0o400) -> Path:
    path.write_text(value, encoding="utf-8")
    path.chmod(mode)
    return path


def test_read_secret_accepts_private_absolute_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_secret(tmp_path / "secret", "x" * 32 + "\n")
    monkeypatch.setenv("TEST_SECRET_FILE", str(path))

    assert (
        read_secret(
            "TEST_SECRET",
            "TEST_SECRET_FILE",
            required=True,
            minimum_characters=32,
        )
        == "x" * 32
    )


def test_read_secret_rejects_broad_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_secret(tmp_path / "secret", "x" * 32, 0o644)
    monkeypatch.setenv("TEST_SECRET_FILE", str(path))

    with pytest.raises(RuntimeError, match="mode 0400 or 0600"):
        read_secret("TEST_SECRET", "TEST_SECRET_FILE")


def test_read_secret_rejects_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = _write_secret(tmp_path / "target", "x" * 32)
    link = tmp_path / "secret"
    link.symlink_to(target)
    monkeypatch.setenv("TEST_SECRET_FILE", str(link))

    with pytest.raises(RuntimeError, match="regular file, not a symlink"):
        read_secret("TEST_SECRET", "TEST_SECRET_FILE")


def test_read_secret_rejects_direct_value_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("TEST_SECRET", "x" * 32)

    with pytest.raises(RuntimeError, match="forbidden in production"):
        read_secret("TEST_SECRET", "TEST_SECRET_FILE")


def test_read_secret_rejects_ambiguous_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_secret(tmp_path / "secret", "x" * 32)
    monkeypatch.setenv("TEST_SECRET", "y" * 32)
    monkeypatch.setenv("TEST_SECRET_FILE", os.fspath(path))

    with pytest.raises(RuntimeError, match="Set only"):
        read_secret("TEST_SECRET", "TEST_SECRET_FILE")
