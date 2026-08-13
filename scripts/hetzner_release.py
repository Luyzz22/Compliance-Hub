#!/usr/bin/env python3
"""Fail-closed release plan and transactional Hetzner Compose cutover."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

if __package__:
    from scripts.verify_release_evidence import (
        _reject_duplicate_json_object,
        read_environment,
        validate_rollback_binding,
    )
else:  # pragma: no cover - exercised by the deployment host entrypoint
    from verify_release_evidence import (  # type: ignore[no-redef]
        _reject_duplicate_json_object,
        read_environment,
        validate_rollback_binding,
    )

MAX_CONTROL_FILE_BYTES = 16 * 1024 * 1024
MAX_SECRET_BYTES = 64 * 1024
RELEASE_LABELS = {
    "COMPLIANCEHUB_RELEASE_ID": "com.complywithai.release.id",
    "COMPLIANCEHUB_RELEASE_COMMIT": "com.complywithai.release.commit",
    "COMPLIANCEHUB_RELEASE_EVIDENCE_SHA256": ("com.complywithai.release.evidence-sha256"),
    "COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256": ("com.complywithai.release.blueprint-sha256"),
}
SERVICE_IMAGES = {
    "backend": "COMPLIANCEHUB_BACKEND_IMAGE",
    "frontend": "COMPLIANCEHUB_FRONTEND_IMAGE",
}


class ReleaseError(RuntimeError):
    """A release gate failed without exposing secret content."""


@dataclass(frozen=True)
class ReleasePaths:
    repository: Path
    deployment: Path
    compose: Path
    candidate_environment: Path
    current_environment: Path
    evidence: Path
    builder_public_key: Path
    approver_public_key: Path
    backend_sbom: Path
    frontend_sbom: Path
    lock_file: Path
    audit_log: Path


def _secure_read(
    path: Path,
    *,
    allowed_modes: set[int],
    allowed_uids: set[int] | None = None,
    maximum_bytes: int = MAX_CONTROL_FILE_BYTES,
) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ReleaseError(f"required file cannot be inspected: {path.name}") from exc
    mode = stat.S_IMODE(metadata.st_mode)
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise ReleaseError(f"required file must be a regular non-symlink: {path.name}")
    if mode not in allowed_modes:
        expected = "/".join(f"{value:04o}" for value in sorted(allowed_modes))
        raise ReleaseError(f"{path.name} must use mode {expected}")
    if allowed_uids is not None and metadata.st_uid not in allowed_uids:
        raise ReleaseError(f"{path.name} has an unapproved owner")
    if metadata.st_size > maximum_bytes:
        raise ReleaseError(f"{path.name} exceeds the maximum control-file size")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ReleaseError(f"required file cannot be opened safely: {path.name}") from exc
    try:
        opened = os.fstat(descriptor)
        if opened.st_dev != metadata.st_dev or opened.st_ino != metadata.st_ino:
            raise ReleaseError(f"required file changed during validation: {path.name}")
        chunks: list[bytes] = []
        remaining = maximum_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 64 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
    finally:
        os.close(descriptor)
    content = b"".join(chunks)
    if len(content) > maximum_bytes:
        raise ReleaseError(f"{path.name} exceeds the maximum control-file size")
    return content


def _load_json(path: Path) -> dict[str, object]:
    content = _secure_read(path, allowed_modes={0o400, 0o440, 0o600, 0o640})
    try:
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ReleaseError(f"{path.name} must be valid JSON without duplicate keys") from exc
    if not isinstance(payload, dict):
        raise ReleaseError(f"{path.name} must contain a JSON object")
    return payload


def _load_environment(path: Path) -> tuple[bytes, dict[str, str]]:
    owners = {0, os.geteuid()}
    content = _secure_read(path, allowed_modes={0o600}, allowed_uids=owners)
    errors: list[str] = []
    environment = read_environment(path, errors)
    if errors:
        raise ReleaseError("; ".join(errors))
    forbidden = [
        key
        for key, value in environment.items()
        if value
        and not key.endswith("_FILE")
        and (
            key.endswith("_PASSWORD")
            or key.endswith("_SECRET")
            or key.endswith("_TOKEN")
            or key.endswith("_API_KEY")
            or key.endswith("_ACCESS_KEY")
            or key.endswith("_PRIVATE_KEY")
        )
    ]
    if forbidden:
        raise ReleaseError(
            "deployment environment contains direct secrets: " + ", ".join(sorted(forbidden))
        )
    return content, environment


def validate_secret_host_contract(deployment: Path, compose_payload: object) -> None:
    if not isinstance(compose_payload, dict):
        raise ReleaseError("compose.yml must contain an object")
    contracts = compose_payload.get("x-secret-host-contract")
    definitions = compose_payload.get("secrets")
    if not isinstance(contracts, dict) or not isinstance(definitions, dict):
        raise ReleaseError("compose.yml must define secrets and x-secret-host-contract")
    if set(contracts) != set(definitions):
        raise ReleaseError("secret host contract must cover every Compose secret exactly")

    deployment_root = deployment.resolve(strict=True)
    for name in sorted(definitions):
        definition = definitions[name]
        contract = contracts[name]
        if not isinstance(definition, dict) or not isinstance(contract, dict):
            raise ReleaseError(f"secret contract is malformed: {name}")
        source = definition.get("file")
        uid = contract.get("uid")
        raw_mode = contract.get("mode")
        if not isinstance(source, str) or type(uid) is not int or raw_mode != "0400":
            raise ReleaseError(f"secret contract is incomplete: {name}")
        source_path = deployment_root / source
        for parent in source_path.parents:
            if parent == deployment_root:
                break
            if parent.is_symlink():
                raise ReleaseError(f"secret source has a symlinked parent: {name}")
        resolved_source = source_path.resolve(strict=False)
        if not resolved_source.is_relative_to(deployment_root):
            raise ReleaseError(f"secret source escapes the deployment directory: {name}")
        content = _secure_read(
            source_path,
            allowed_modes={0o400},
            allowed_uids={uid},
            maximum_bytes=MAX_SECRET_BYTES,
        )
        if not content.strip():
            raise ReleaseError(f"secret source must not be empty: {name}")


def _secret_source(deployment: Path, compose_payload: object, name: str) -> Path:
    if not isinstance(compose_payload, dict) or not isinstance(
        compose_payload.get("secrets"), dict
    ):
        raise ReleaseError("Compose secret definitions are unavailable")
    definition = compose_payload["secrets"].get(name)
    if not isinstance(definition, dict) or not isinstance(definition.get("file"), str):
        raise ReleaseError(f"Compose secret is unavailable: {name}")
    return deployment / definition["file"]


def validate_certificate_contract(
    deployment: Path,
    compose_payload: object,
    environment: dict[str, str],
) -> None:
    """Validate certificate lifetime, hostname, key material and TLS key pairing."""

    hostname = environment.get("COMPLIANCEHUB_PUBLIC_HOST", "")
    if not hostname or any(character in hostname for character in "/:@[]"):
        raise ReleaseError("COMPLIANCEHUB_PUBLIC_HOST is invalid for certificate validation")
    tls_certificate = _secret_source(deployment, compose_payload, "tls_certificate")
    tls_private_key = _secret_source(deployment, compose_payload, "tls_private_key")
    azure_certificate = _secret_source(
        deployment,
        compose_payload,
        "azure_openai_client_certificate",
    )
    for certificate in (tls_certificate, azure_certificate):
        _run(
            ["openssl", "x509", "-in", str(certificate), "-checkend", "2592000", "-noout"],
            cwd=deployment,
        )
    _run(
        ["openssl", "x509", "-in", str(tls_certificate), "-checkhost", hostname, "-noout"],
        cwd=deployment,
    )
    tls_public_key = _run(
        ["openssl", "x509", "-in", str(tls_certificate), "-pubkey", "-noout"],
        cwd=deployment,
    )
    private_public_key = _run(
        [
            "openssl",
            "pkey",
            "-in",
            str(tls_private_key),
            "-passin",
            "pass:",
            "-pubout",
        ],
        cwd=deployment,
    )
    if tls_public_key != private_public_key:
        raise ReleaseError("TLS certificate and private key do not match")
    _run(
        [
            "openssl",
            "pkey",
            "-in",
            str(tls_private_key),
            "-passin",
            "pass:",
            "-check",
            "-noout",
        ],
        cwd=deployment,
    )
    _run(
        [
            "openssl",
            "pkey",
            "-in",
            str(azure_certificate),
            "-passin",
            "pass:",
            "-check",
            "-noout",
        ],
        cwd=deployment,
    )


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
) -> str:
    try:
        result = subprocess.run(
            list(command),
            cwd=cwd,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReleaseError(f"command could not complete: {command[0]}") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise ReleaseError(f"command failed ({command[0]}): {detail or 'no diagnostic'}")
    return result.stdout.strip()


def _compose_command(paths: ReleasePaths, env_file: Path, *arguments: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-directory",
        str(paths.deployment),
        "--env-file",
        str(env_file),
        "-f",
        str(paths.compose),
        *arguments,
    ]


def _compose_environment(env_file: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment["COMPLIANCEHUB_ENV_FILE"] = str(env_file)
    return environment


def _verify_release_evidence(paths: ReleasePaths) -> None:
    output = _run(
        [
            sys.executable,
            str(paths.repository / "scripts" / "verify_release_evidence.py"),
            str(paths.evidence),
            "--expected-commit",
            "HEAD",
            "--deployment-env",
            str(paths.candidate_environment),
            "--builder-public-key",
            str(paths.builder_public_key),
            "--approver-public-key",
            str(paths.approver_public_key),
            "--backend-sbom",
            str(paths.backend_sbom),
            "--frontend-sbom",
            str(paths.frontend_sbom),
            "--deployment-dir",
            str(paths.deployment),
            "--json",
        ],
        cwd=paths.repository,
    )
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ReleaseError("release evidence verifier returned invalid output") from exc
    if payload != {"passed": True, "errors": []}:
        raise ReleaseError("release evidence verification did not pass")


def _verify_clean_release_checkout(paths: ReleasePaths) -> None:
    root = _run(["git", "rev-parse", "--show-toplevel"], cwd=paths.repository)
    if Path(root).resolve() != paths.repository.resolve():
        raise ReleaseError("release checkout root does not match the controller repository")
    dirty = _run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=paths.repository,
    )
    if dirty:
        raise ReleaseError("release checkout must be clean and fully committed")


def _validate_compose(paths: ReleasePaths, env_file: Path) -> None:
    _run(
        _compose_command(paths, env_file, "config", "--quiet"),
        cwd=paths.deployment,
        environment=_compose_environment(env_file),
    )


def preflight(paths: ReleasePaths) -> tuple[dict[str, object], bytes, dict[str, str]]:
    """Run every non-mutating gate and return the verified rollback snapshot."""

    if paths.candidate_environment == paths.current_environment:
        raise ReleaseError("candidate and current environment files must differ")
    _verify_clean_release_checkout(paths)
    _candidate_bytes, candidate_environment = _load_environment(paths.candidate_environment)
    current_bytes, current_environment = _load_environment(paths.current_environment)
    for control_path, modes, owners in (
        (paths.evidence, {0o400, 0o440, 0o600, 0o640}, {0, os.geteuid()}),
        (paths.builder_public_key, {0o400, 0o440, 0o444}, {0}),
        (paths.approver_public_key, {0o400, 0o440, 0o444}, {0}),
        (paths.backend_sbom, {0o400, 0o440, 0o444}, {0, os.geteuid()}),
        (paths.frontend_sbom, {0o400, 0o440, 0o444}, {0, os.geteuid()}),
    ):
        _secure_read(control_path, allowed_modes=modes, allowed_uids=owners)
    compose_bytes = _secure_read(paths.compose, allowed_modes={0o444, 0o644})
    try:
        compose_payload = yaml.safe_load(compose_bytes.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise ReleaseError("compose.yml must be valid YAML") from exc
    validate_secret_host_contract(paths.deployment, compose_payload)
    validate_certificate_contract(
        paths.deployment,
        compose_payload,
        candidate_environment,
    )
    _verify_release_evidence(paths)
    evidence = _load_json(paths.evidence)
    rollback_errors = validate_rollback_binding(evidence, current_environment)
    if rollback_errors:
        raise ReleaseError("; ".join(rollback_errors))
    _validate_compose(paths, paths.candidate_environment)
    _validate_compose(paths, paths.current_environment)
    return evidence, current_bytes, current_environment


def _atomic_replace(path: Path, content: bytes) -> None:
    descriptor, raw_temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw_temporary)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def _ensure_secure_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = path.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or metadata.st_uid not in {0, os.geteuid()}
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise ReleaseError(f"{path.name} must be an owner-only regular directory")


def _audit_event(path: Path, *, release_id: str, action: str, outcome: str) -> None:
    previous_hash = "0" * 64
    existing = b""
    if path.exists():
        existing = _secure_read(
            path,
            allowed_modes={0o600},
            allowed_uids={0, os.geteuid()},
        )
        for line in existing.splitlines():
            try:
                event = json.loads(line, object_pairs_hook=_reject_duplicate_json_object)
            except (json.JSONDecodeError, ValueError) as exc:
                raise ReleaseError("release audit log is malformed") from exc
            if not isinstance(event, dict) or event.get("previous_sha256") != previous_hash:
                raise ReleaseError("release audit log hash chain is invalid")
            recorded_hash = event.pop("event_sha256", None)
            computed_hash = hashlib.sha256(
                json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if recorded_hash != computed_hash:
                raise ReleaseError("release audit log hash chain is invalid")
            previous_hash = computed_hash

    event: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "release_id": release_id,
        "action": action,
        "outcome": outcome,
        "actor_uid": os.geteuid(),
        "previous_sha256": previous_hash,
    }
    event["event_sha256"] = hashlib.sha256(
        json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    serialized = json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
    _ensure_secure_directory(path.parent)
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_APPEND
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = os.open(path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid not in {0, os.geteuid()}
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ReleaseError("release audit log must be owner-only regular storage")
        encoded = serialized.encode("utf-8")
        written = 0
        while written < len(encoded):
            count = os.write(descriptor, encoded[written:])
            if count <= 0:
                raise ReleaseError("release audit log write did not complete")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


@contextmanager
def exclusive_release_lock(path: Path) -> Iterator[None]:
    _ensure_secure_directory(path.parent)
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise ReleaseError("release lock must be a regular file with mode 0600")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ReleaseError("another release operation already holds the lock") from exc
        yield
    finally:
        os.close(descriptor)


def _verify_runtime_artifacts(paths: ReleasePaths, environment: dict[str, str]) -> None:
    compose_environment = _compose_environment(paths.current_environment)
    for service in ("backend", "frontend"):
        container_id = _run(
            _compose_command(paths, paths.current_environment, "ps", "-q", service),
            cwd=paths.deployment,
            environment=compose_environment,
        )
        if not container_id:
            raise ReleaseError(f"{service} container is not running")
        configured_image = _run(
            ["docker", "inspect", "--format", "{{.Config.Image}}", container_id],
            cwd=paths.deployment,
        )
        if configured_image != environment.get(SERVICE_IMAGES[service]):
            raise ReleaseError(f"{service} runtime image is not release-bound")
        labels_raw = _run(
            ["docker", "inspect", "--format", "{{json .Config.Labels}}", container_id],
            cwd=paths.deployment,
        )
        try:
            labels = json.loads(labels_raw)
        except json.JSONDecodeError as exc:
            raise ReleaseError(f"{service} runtime labels cannot be verified") from exc
        for env_key, label_key in RELEASE_LABELS.items():
            if labels.get(label_key) != environment.get(env_key):
                raise ReleaseError(f"{service} runtime label {label_key} is not release-bound")


def _probe_edge(environment: dict[str, str], deployment: Path) -> None:
    host = environment.get("COMPLIANCEHUB_PUBLIC_HOST", "")
    if not host or any(character in host for character in "/:@[]"):
        raise ReleaseError("COMPLIANCEHUB_PUBLIC_HOST is invalid for the edge probe")
    _run(
        [
            "curl",
            "--proto",
            "=https",
            "--tlsv1.2",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            "15",
            "--resolve",
            f"{host}:443:127.0.0.1",
            f"https://{host}/",
        ],
        cwd=deployment,
    )


def apply_release(
    paths: ReleasePaths,
    *,
    evidence: dict[str, object],
    current_bytes: bytes,
    candidate_bytes: bytes,
    candidate_environment: dict[str, str],
    wait_timeout: int,
) -> None:
    release_id = str(evidence["release_id"])
    candidate_compose_env = _compose_environment(paths.candidate_environment)
    current_compose_env = _compose_environment(paths.current_environment)
    current_environment = _load_environment(paths.current_environment)[1]
    promoted = False
    _audit_event(paths.audit_log, release_id=release_id, action="cutover", outcome="started")
    try:
        _run(["docker", "info", "--format", "{{.ServerVersion}}"], cwd=paths.deployment)
        _verify_runtime_artifacts(paths, current_environment)
        _probe_edge(current_environment, paths.deployment)
        _run(
            _compose_command(paths, paths.current_environment, "pull", "backend", "frontend"),
            cwd=paths.deployment,
            environment=current_compose_env,
        )
        _run(
            _compose_command(paths, paths.candidate_environment, "pull"),
            cwd=paths.deployment,
            environment=candidate_compose_env,
        )
        _run(
            _compose_command(
                paths,
                paths.candidate_environment,
                "run",
                "--rm",
                "--no-deps",
                "frontend",
                "node",
                "scripts/verify-enterprise-readiness.mjs",
            ),
            cwd=paths.deployment,
            environment=candidate_compose_env,
        )
        _run(
            _compose_command(
                paths,
                paths.candidate_environment,
                "run",
                "--rm",
                "--no-deps",
                "backend",
                "python",
                "/app/scripts/verify_db_schema.py",
            ),
            cwd=paths.deployment,
            environment=candidate_compose_env,
        )
        _atomic_replace(paths.current_environment, candidate_bytes)
        promoted = True
        _run(
            _compose_command(
                paths,
                paths.current_environment,
                "up",
                "-d",
                "--no-build",
                "--wait",
                "--wait-timeout",
                str(wait_timeout),
                "--remove-orphans",
            ),
            cwd=paths.deployment,
            environment=current_compose_env,
        )
        _verify_runtime_artifacts(paths, candidate_environment)
        _probe_edge(candidate_environment, paths.deployment)
    except ReleaseError as cutover_error:
        if not promoted:
            _audit_event(paths.audit_log, release_id=release_id, action="cutover", outcome="failed")
            raise
        _atomic_replace(paths.current_environment, current_bytes)
        try:
            _run(
                _compose_command(
                    paths,
                    paths.current_environment,
                    "up",
                    "-d",
                    "--no-build",
                    "--wait",
                    "--wait-timeout",
                    str(wait_timeout),
                    "--remove-orphans",
                ),
                cwd=paths.deployment,
                environment=current_compose_env,
            )
            _verify_runtime_artifacts(paths, current_environment)
            _probe_edge(current_environment, paths.deployment)
        except ReleaseError as rollback_error:
            _audit_event(
                paths.audit_log,
                release_id=release_id,
                action="rollback",
                outcome="failed",
            )
            raise ReleaseError(
                f"cutover failed and rollback failed: {type(rollback_error).__name__}"
            ) from cutover_error
        _audit_event(
            paths.audit_log,
            release_id=release_id,
            action="rollback",
            outcome="succeeded",
        )
        raise ReleaseError("cutover failed; the verified previous environment was restored") from (
            cutover_error
        )
    _audit_event(paths.audit_log, release_id=release_id, action="cutover", outcome="succeeded")


def _resolve_paths(arguments: argparse.Namespace) -> ReleasePaths:
    repository = Path(__file__).resolve().parents[1]
    deployment = Path(arguments.deployment_dir).resolve()

    def resolve(raw: str) -> Path:
        path = Path(raw)
        return path.resolve() if path.is_absolute() else (deployment / path).resolve()

    return ReleasePaths(
        repository=repository,
        deployment=deployment,
        compose=deployment / "compose.yml",
        candidate_environment=resolve(arguments.candidate_env),
        current_environment=resolve(arguments.current_env),
        evidence=resolve(arguments.evidence),
        builder_public_key=resolve(arguments.builder_public_key),
        approver_public_key=resolve(arguments.approver_public_key),
        backend_sbom=resolve(arguments.backend_sbom),
        frontend_sbom=resolve(arguments.frontend_sbom),
        lock_file=Path(arguments.lock_file).resolve(),
        audit_log=Path(arguments.audit_log).resolve(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("plan", "apply"))
    parser.add_argument("--deployment-dir", default="deploy/hetzner")
    parser.add_argument("--candidate-env", default=".env.candidate")
    parser.add_argument("--current-env", default=".env.production")
    parser.add_argument("--evidence", default="release-evidence.json")
    parser.add_argument(
        "--builder-public-key",
        default="/etc/compliancehub/release-trust/builder-ed25519.pem",
    )
    parser.add_argument(
        "--approver-public-key",
        default="/etc/compliancehub/release-trust/approver-ed25519.pem",
    )
    parser.add_argument("--backend-sbom", default="artifacts/backend.cdx.json")
    parser.add_argument("--frontend-sbom", default="artifacts/frontend.cdx.json")
    parser.add_argument("--lock-file", default="/var/lock/compliancehub/release.lock")
    parser.add_argument("--audit-log", default="/var/log/compliancehub/release-events.jsonl")
    parser.add_argument("--confirm-release-id")
    parser.add_argument("--wait-timeout", type=int, default=180)
    arguments = parser.parse_args()
    if not 30 <= arguments.wait_timeout <= 900:
        parser.error("--wait-timeout must be between 30 and 900 seconds")
    paths = _resolve_paths(arguments)

    try:
        with exclusive_release_lock(paths.lock_file):
            evidence, current_bytes, _current_environment = preflight(paths)
            candidate_bytes, candidate_environment = _load_environment(paths.candidate_environment)
            release_id = str(evidence.get("release_id", ""))
            if arguments.operation == "apply":
                if arguments.confirm_release_id != release_id:
                    raise ReleaseError(
                        "--confirm-release-id must exactly match the verified release"
                    )
                apply_release(
                    paths,
                    evidence=evidence,
                    current_bytes=current_bytes,
                    candidate_bytes=candidate_bytes,
                    candidate_environment=candidate_environment,
                    wait_timeout=arguments.wait_timeout,
                )
            print(
                json.dumps(
                    {
                        "passed": True,
                        "operation": arguments.operation,
                        "release_id": release_id,
                        "mutated_runtime": arguments.operation == "apply",
                    },
                    sort_keys=True,
                )
            )
            return 0
    except ReleaseError as exc:
        print(
            json.dumps(
                {
                    "passed": False,
                    "operation": arguments.operation,
                    "error": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
