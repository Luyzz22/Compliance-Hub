"""Contracts for the Hetzner-only signed image builder."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import sovereign_release_build


def _config(tmp_path: Path) -> Path:
    path = tmp_path / "release-builder.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "registry_prefix": "registry.internal.example.de/compliancehub",
                "allowed_registry_hosts": ["registry.internal.example.de"],
                "base_images": {
                    "backend": "registry.internal.example.de/mirror/python@sha256:" + "a" * 64,
                    "frontend": "registry.internal.example.de/mirror/node@sha256:" + "b" * 64,
                },
                "package_mirrors": {
                    "python": "https://packages.internal.example.de/pypi/simple",
                    "npm": "https://packages.internal.example.de/npm/",
                },
                "allowed_package_hosts": ["packages.internal.example.de"],
                "trivy_cache_dir": str(tmp_path / "trivy-cache"),
                "trivy_db_max_age_hours": 24,
                "evidence_root": str(tmp_path / "evidence"),
                "openbao_address": "https://openbao.internal.example.de:8200",
                "openbao_transit_key": "compliancehub-release",
                "openbao_token_file": str(tmp_path / "openbao-token"),
                "cosign_public_key": str(tmp_path / "cosign.pub"),
                "required_tools": {
                    "cosign": "v3.0.6",
                    "syft": "1.50.0",
                    "trivy": "0.73.0",
                },
            }
        ),
        encoding="utf-8",
    )
    path.chmod(0o400)
    return path


def test_builder_config_accepts_only_explicit_private_registry(tmp_path: Path) -> None:
    path = _config(tmp_path)
    config = sovereign_release_build.load_builder_config(path, allowed_uids={os.geteuid()})
    assert config["registry_prefix"] == "registry.internal.example.de/compliancehub"

    payload = json.loads(path.read_text(encoding="utf-8"))
    path.chmod(0o600)
    payload["registry_prefix"] = "ghcr.io/luyzz22/compliancehub"
    payload["allowed_registry_hosts"] = ["ghcr.io"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o400)
    with pytest.raises(sovereign_release_build.BuildError, match="private registry"):
        sovereign_release_build.load_builder_config(path, allowed_uids={os.geteuid()})


def test_builder_config_requires_internal_package_and_base_image_mirrors(
    tmp_path: Path,
) -> None:
    path = _config(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    path.chmod(0o600)
    payload["package_mirrors"]["npm"] = "https://registry.npmjs.org/"
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o400)
    with pytest.raises(sovereign_release_build.BuildError, match="package mirror"):
        sovereign_release_build.load_builder_config(path, allowed_uids={os.geteuid()})

    path.chmod(0o600)
    payload["package_mirrors"]["npm"] = "https://packages.internal.example.de/npm/"
    payload["base_images"]["backend"] = "python:3.11@sha256:" + "a" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    path.chmod(0o400)
    with pytest.raises(sovereign_release_build.BuildError, match="base image"):
        sovereign_release_build.load_builder_config(path, allowed_uids={os.geteuid()})


def test_evidence_directory_is_owner_only_and_unique(tmp_path: Path) -> None:
    root = tmp_path / "evidence"
    root.mkdir(mode=0o700)
    result = sovereign_release_build._ensure_evidence_directory(root, "a" * 40, "run-1")
    assert result.stat().st_uid == os.geteuid()
    assert result.stat().st_mode & 0o777 == 0o700
    with pytest.raises(FileExistsError):
        sovereign_release_build._ensure_evidence_directory(root, "a" * 40, "run-1")


def _trivy_cache(tmp_path: Path, *, updated_at: datetime, next_update: datetime) -> Path:
    cache = tmp_path / "trivy-cache"
    database_dir = cache / "db"
    database_dir.mkdir(parents=True, mode=0o700)
    cache.chmod(0o700)
    database = database_dir / "trivy.db"
    database.write_bytes(b"0" * 1024)
    database.chmod(0o400)
    metadata = database_dir / "metadata.json"
    metadata.write_text(
        json.dumps(
            {
                "UpdatedAt": updated_at.isoformat().replace("+00:00", "Z"),
                "NextUpdate": next_update.isoformat().replace("+00:00", "Z"),
            }
        ),
        encoding="utf-8",
    )
    metadata.chmod(0o400)
    return cache


def test_trivy_cache_requires_fresh_preprovisioned_database(tmp_path: Path) -> None:
    now = datetime(2026, 8, 13, 12, tzinfo=UTC)
    cache = _trivy_cache(
        tmp_path,
        updated_at=now - timedelta(hours=1),
        next_update=now + timedelta(hours=5),
    )
    sovereign_release_build._validate_trivy_cache(
        cache,
        maximum_age_hours=24,
        allowed_uids={os.geteuid()},
        now=now,
    )

    metadata = cache / "db" / "metadata.json"
    metadata.chmod(0o600)
    metadata.write_text(
        json.dumps(
            {
                "UpdatedAt": (now - timedelta(hours=25)).isoformat(),
                "NextUpdate": (now - timedelta(hours=19)).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    metadata.chmod(0o400)
    with pytest.raises(sovereign_release_build.BuildError, match="stale"):
        sovereign_release_build._validate_trivy_cache(
            cache,
            maximum_age_hours=24,
            allowed_uids={os.geteuid()},
            now=now,
        )


def test_preproduction_workflow_never_uploads_sovereign_artifacts() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / ".github/workflows/preproduction-build.yml").read_text(encoding="utf-8")
    assert "runs-on: [self-hosted, linux, x64, compliancehub-hetzner-release]" in source
    assert "environment: preproduction" in source
    assert "github.ref == 'refs/heads/main'" in source
    assert "actions/upload-artifact" not in source
    assert "persist-credentials: false" in source
    assert "COMPLIANCEHUB_RELEASE_BUILDER_CONFIG: /etc/compliancehub/release-builder.json" in source


def test_builder_uses_openbao_transit_and_private_infrastructure_verification() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "scripts/sovereign_release_build.py").read_text(encoding="utf-8")
    assert 'kms_key = f"openbao://{transit_key}"' in source
    assert source.count('"--tlog-upload=false"') == 2
    assert source.count('"--use-signing-config=false"') == 2
    assert '"--skip-db-update"' in source
    assert '"--offline-scan"' in source
    assert source.count('"--private-infrastructure"') == 3
    assert '"slsaprovenance1"' in source
    assert '"cyclonedx"' in source
    assert '"BAO_TOKEN": token' in source
