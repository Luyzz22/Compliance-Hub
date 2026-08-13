"""Adversarial tests for the transactional Hetzner release controller."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path

import pytest

from scripts import hetzner_release


def _paths(tmp_path: Path) -> hetzner_release.ReleasePaths:
    deployment = tmp_path / "deploy"
    deployment.mkdir()
    return hetzner_release.ReleasePaths(
        repository=tmp_path,
        deployment=deployment,
        compose=deployment / "compose.yml",
        candidate_environment=deployment / ".env.candidate",
        current_environment=deployment / ".env.production",
        evidence=deployment / "release-evidence.json",
        builder_public_key=deployment / "builder.pem",
        approver_public_key=deployment / "approver.pem",
        backend_sbom=deployment / "backend.cdx.json",
        frontend_sbom=deployment / "frontend.cdx.json",
        restore_evidence=deployment / "restore-drill.json",
        lock_file=tmp_path / "lock" / "release.lock",
        audit_log=tmp_path / "log" / "release.jsonl",
    )


def _write(path: Path, content: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(mode)


def test_environment_loader_rejects_direct_secrets_and_weak_permissions(
    tmp_path: Path,
) -> None:
    environment = tmp_path / ".env.production"
    _write(
        environment,
        b"DATABASE_PASSWORD=not-allowed\nCOMPLIANCEHUB_S3_ACCESS_KEY=also-forbidden\n",
        0o600,
    )

    with pytest.raises(hetzner_release.ReleaseError, match="direct secrets"):
        hetzner_release._load_environment(environment)

    _write(environment, b"COMPLIANCEHUB_RELEASE_ID=REL-1\n", 0o644)
    with pytest.raises(hetzner_release.ReleaseError, match="0600"):
        hetzner_release._load_environment(environment)


def test_secret_contract_rejects_symlinks_wrong_modes_and_empty_files(
    tmp_path: Path,
) -> None:
    deployment = tmp_path / "deploy"
    secrets = deployment / "secrets"
    secrets.mkdir(parents=True)
    secret = secrets / "api-key"
    _write(secret, b"a" * 32, 0o400)
    payload = {
        "x-secret-host-contract": {
            "api_key": {
                "uid": os.geteuid(),
                "mode": "0400",
                "min_bytes": 32,
                "content_kind": "opaque",
                "consumers": ["api"],
                "rotation_policy": "standard_90d",
            }
        },
        "secrets": {"api_key": {"file": "./secrets/api-key"}},
        "services": {"api": {"secrets": [{"source": "api_key", "target": "api_key"}]}},
    }

    hetzner_release.validate_secret_host_contract(deployment, payload)

    secret.chmod(0o600)
    with pytest.raises(hetzner_release.ReleaseError, match="0400"):
        hetzner_release.validate_secret_host_contract(deployment, payload)
    secret.unlink()
    _write(secret, b"", 0o400)
    with pytest.raises(hetzner_release.ReleaseError, match="must not be empty"):
        hetzner_release.validate_secret_host_contract(deployment, payload)
    secret.unlink()
    target = secrets / "real-key"
    _write(target, b"a" * 32, 0o400)
    secret.symlink_to(target)
    with pytest.raises(hetzner_release.ReleaseError, match="non-symlink"):
        hetzner_release.validate_secret_host_contract(deployment, payload)


def test_secret_contract_rejects_weak_content_and_undeclared_consumers(
    tmp_path: Path,
) -> None:
    deployment = tmp_path / "deploy"
    secret = deployment / "secrets" / "database-url"
    _write(secret, b"too-short", 0o400)
    payload = {
        "x-secret-host-contract": {
            "database_url": {
                "uid": os.geteuid(),
                "mode": "0400",
                "min_bytes": 32,
                "content_kind": "postgres_dsn",
                "consumers": ["backend"],
                "rotation_policy": "standard_90d",
            }
        },
        "secrets": {"database_url": {"file": "./secrets/database-url"}},
        "services": {
            "backend": {"secrets": [{"source": "database_url", "target": "database_url"}]}
        },
    }

    with pytest.raises(hetzner_release.ReleaseError, match="minimum length"):
        hetzner_release.validate_secret_host_contract(deployment, payload)

    secret.chmod(0o600)
    _write(secret, b"postgresql://runtime:long-secret-value@db.internal/app", 0o400)
    hetzner_release.validate_secret_host_contract(deployment, payload)

    payload["services"]["worker"] = {
        "secrets": [{"source": "database_url", "target": "database_url"}]
    }
    with pytest.raises(hetzner_release.ReleaseError, match="consumer contract"):
        hetzner_release.validate_secret_host_contract(deployment, payload)


def test_release_lock_rejects_concurrent_operator(tmp_path: Path) -> None:
    directory = tmp_path / "lock"
    directory.mkdir(mode=0o700)
    lock = directory / "release.lock"
    descriptor = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(hetzner_release.ReleaseError, match="already holds"):
            with hetzner_release.exclusive_release_lock(lock):
                pass
    finally:
        os.close(descriptor)


def test_audit_log_is_hash_chained_and_tampering_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "audit" / "events.jsonl"
    hetzner_release._audit_event(
        path,
        release_id="REL-1",
        action="cutover",
        outcome="started",
    )
    hetzner_release._audit_event(
        path,
        release_id="REL-1",
        action="cutover",
        outcome="succeeded",
    )
    lines = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert second["previous_sha256"] == first["event_sha256"]

    path.write_text(lines[0].replace("started", "tampered") + "\n", encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(hetzner_release.ReleaseError, match="hash chain"):
        hetzner_release._audit_event(
            path,
            release_id="REL-2",
            action="cutover",
            outcome="started",
        )


def test_plan_preflight_uses_only_read_only_commands(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    _write(paths.candidate_environment, b"RELEASE=candidate\n")
    _write(paths.current_environment, b"RELEASE=current\n")
    _write(paths.compose, b"services: {}\n", 0o644)
    evidence = {"release_id": "REL-2"}
    calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(hetzner_release, "_verify_clean_release_checkout", lambda _paths: None)
    monkeypatch.setattr(hetzner_release, "validate_secret_host_contract", lambda *_args: None)
    monkeypatch.setattr(hetzner_release, "validate_certificate_contract", lambda *_args: None)
    monkeypatch.setattr(hetzner_release, "_verify_release_evidence", lambda _paths: None)
    monkeypatch.setattr(hetzner_release, "_load_json", lambda _path: evidence)
    monkeypatch.setattr(hetzner_release, "validate_rollback_binding", lambda *_args: [])
    monkeypatch.setattr(
        hetzner_release,
        "_secure_read",
        lambda path, **_kwargs: path.read_bytes() if path.exists() else b"control",
    )
    monkeypatch.setattr(
        hetzner_release,
        "_run",
        lambda command, **_kwargs: calls.append(tuple(command)) or "",
    )

    result = hetzner_release.preflight(paths)

    assert result[0] == evidence
    assert calls
    assert all("config" in command and "--quiet" in command for command in calls)
    assert all(not {"pull", "up", "run"}.intersection(command) for command in calls)


def test_failed_promoted_cutover_restores_environment_and_verifies_rollback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    current = b"COMPLIANCEHUB_PUBLIC_HOST=app.example.de\nRELEASE=old\n"
    candidate = b"COMPLIANCEHUB_PUBLIC_HOST=app.example.de\nRELEASE=new\n"
    _write(paths.current_environment, current)
    calls: list[tuple[str, ...]] = []
    up_calls = 0

    def fake_run(command, **_kwargs):
        nonlocal up_calls
        calls.append(tuple(command))
        if "up" in command:
            up_calls += 1
            if up_calls == 1:
                raise hetzner_release.ReleaseError("candidate readiness failed")
        return "ok"

    monkeypatch.setattr(hetzner_release, "_run", fake_run)
    monkeypatch.setattr(hetzner_release, "_verify_runtime_artifacts", lambda *_args: None)
    monkeypatch.setattr(hetzner_release, "_probe_edge", lambda *_args: None)
    monkeypatch.setattr(hetzner_release, "_audit_event", lambda *_args, **_kwargs: None)

    with pytest.raises(hetzner_release.ReleaseError, match="previous environment was restored"):
        hetzner_release.apply_release(
            paths,
            evidence={"release_id": "REL-2"},
            current_bytes=current,
            candidate_bytes=candidate,
            candidate_environment={"COMPLIANCEHUB_PUBLIC_HOST": "app.example.de"},
            wait_timeout=60,
        )

    assert paths.current_environment.read_bytes() == current
    assert up_calls == 2
    assert any("scripts/verify-enterprise-readiness.mjs" in command for command in calls)
    assert any("/app/scripts/verify_db_schema.py" in command for command in calls)


def test_certificate_contract_requires_matching_tls_keys_and_azure_private_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    deployment = tmp_path / "deploy"
    deployment.mkdir()
    payload = {
        "secrets": {
            "tls_certificate": {"file": "tls.pem"},
            "tls_private_key": {"file": "tls-key.pem"},
            "azure_openai_client_certificate": {"file": "azure.pem"},
        }
    }
    calls: list[tuple[str, ...]] = []

    def fake_run(command, **_kwargs):
        calls.append(tuple(command))
        if "-pubkey" in command or "-pubout" in command:
            return "matching-public-key"
        return ""

    monkeypatch.setattr(hetzner_release, "_run", fake_run)

    hetzner_release.validate_certificate_contract(
        deployment,
        payload,
        {"COMPLIANCEHUB_PUBLIC_HOST": "app.complywithai.de"},
    )

    assert any("-checkhost" in command for command in calls)
    assert sum("-check" in command for command in calls) == 2
    assert all("2592000" in command for command in calls if "-checkend" in command)


def test_runtime_artifact_verification_binds_image_and_every_release_label(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    paths = _paths(tmp_path)
    environment = {
        "COMPLIANCEHUB_BACKEND_IMAGE": "registry.invalid/backend@sha256:" + "a" * 64,
        "COMPLIANCEHUB_FRONTEND_IMAGE": "registry.invalid/frontend@sha256:" + "b" * 64,
        "COMPLIANCEHUB_RELEASE_ID": "REL-2",
        "COMPLIANCEHUB_RELEASE_COMMIT": "c" * 40,
        "COMPLIANCEHUB_RELEASE_EVIDENCE_SHA256": "d" * 64,
        "COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256": "e" * 64,
    }
    service_for_container = {"backend-id": "backend", "frontend-id": "frontend"}
    actual_images = {
        "backend": environment["COMPLIANCEHUB_BACKEND_IMAGE"],
        "frontend": environment["COMPLIANCEHUB_FRONTEND_IMAGE"],
    }

    def fake_run(command, **_kwargs):
        if "ps" in command:
            service = command[-1]
            return f"{service}-id"
        container_id = command[-1]
        service = service_for_container[container_id]
        if "{{.Config.Image}}" in command:
            return actual_images[service]
        return json.dumps(
            {label: environment[key] for key, label in hetzner_release.RELEASE_LABELS.items()}
        )

    monkeypatch.setattr(hetzner_release, "_run", fake_run)

    hetzner_release._verify_runtime_artifacts(paths, environment)

    environment["COMPLIANCEHUB_FRONTEND_IMAGE"] = "registry.invalid/wrong@sha256:" + "f" * 64
    with pytest.raises(hetzner_release.ReleaseError, match="runtime image"):
        hetzner_release._verify_runtime_artifacts(paths, environment)
