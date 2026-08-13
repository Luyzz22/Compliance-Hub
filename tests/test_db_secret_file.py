"""Database URL secret-file boundary for Hetzner/OpenBao deployments."""

from __future__ import annotations

import pytest

from app.db import get_database_url


def test_database_url_can_be_loaded_from_private_secret_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    secret = tmp_path / "database-url"
    secret.write_text("postgresql://runtime:secret@postgres.internal/compliancehub\n")
    secret.chmod(0o600)
    monkeypatch.delenv("COMPLIANCEHUB_DB_URL", raising=False)
    monkeypatch.setenv("COMPLIANCEHUB_DB_URL_FILE", str(secret))

    assert get_database_url() == "postgresql://runtime:secret@postgres.internal/compliancehub"


def test_database_url_rejects_ambiguous_or_public_secret_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    secret = tmp_path / "database-url"
    secret.write_text("postgresql://runtime:secret@postgres.internal/compliancehub")
    secret.chmod(0o644)
    monkeypatch.setenv("COMPLIANCEHUB_DB_URL_FILE", str(secret))
    monkeypatch.delenv("COMPLIANCEHUB_DB_URL", raising=False)
    with pytest.raises(RuntimeError, match="0400 or 0600"):
        get_database_url()

    secret.chmod(0o600)
    monkeypatch.setenv("COMPLIANCEHUB_DB_URL", "sqlite:///ambiguous.db")
    with pytest.raises(RuntimeError, match="Set only"):
        get_database_url()
