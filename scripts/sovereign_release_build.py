#!/usr/bin/env python3
"""Build and attest release images entirely inside the Hetzner trust boundary."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat

# Fixed argv execution is required for the explicitly approved release tools.
import subprocess  # nosec B404
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

MAX_CONFIG_BYTES = 64 * 1024
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
INVOCATION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
REGISTRY_PREFIX_PATTERN = re.compile(
    r"(?P<host>[a-z0-9.-]+(?::[0-9]{2,5})?)/(?P<path>[a-z0-9._/-]+)"
)
FORBIDDEN_REGISTRY_HOSTS = {
    "docker.io",
    "ghcr.io",
    "quay.io",
    "gcr.io",
    "registry.gitlab.com",
}
CONFIG_FIELDS = {
    "schema_version",
    "registry_prefix",
    "allowed_registry_hosts",
    "base_images",
    "package_mirrors",
    "allowed_package_hosts",
    "trivy_cache_dir",
    "trivy_db_max_age_hours",
    "evidence_root",
    "openbao_address",
    "openbao_transit_key",
    "openbao_token_file",
    "cosign_public_key",
    "required_tools",
}
BASE_IMAGE_PATTERN = re.compile(
    r"(?P<host>[a-z0-9.-]+(?::[0-9]{2,5})?)/[a-z0-9._/-]+@sha256:[0-9a-f]{64}"
)
FORBIDDEN_PACKAGE_HOSTS = {
    "files.pythonhosted.org",
    "pypi.org",
    "registry.npmjs.org",
}


class BuildError(RuntimeError):
    """The sovereign build failed without disclosing secret material."""


def _secure_read(
    path: Path,
    *,
    allowed_modes: set[int],
    allowed_uids: set[int],
    maximum_bytes: int = MAX_CONFIG_BYTES,
) -> bytes:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise BuildError(f"required control file cannot be inspected: {path.name}") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or stat.S_IMODE(metadata.st_mode) not in allowed_modes
        or metadata.st_uid not in allowed_uids
        or metadata.st_size > maximum_bytes
    ):
        raise BuildError(f"required control file has an unsafe contract: {path.name}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BuildError(f"required control file cannot be opened: {path.name}") from exc
    try:
        opened = os.fstat(descriptor)
        if opened.st_dev != metadata.st_dev or opened.st_ino != metadata.st_ino:
            raise BuildError(f"required control file changed during validation: {path.name}")
        content = os.read(descriptor, maximum_bytes + 1)
    finally:
        os.close(descriptor)
    if len(content) > maximum_bytes:
        raise BuildError(f"required control file is too large: {path.name}")
    return content


def _secure_file_metadata(
    path: Path,
    *,
    allowed_modes: set[int],
    allowed_uids: set[int],
    minimum_bytes: int,
    maximum_bytes: int,
) -> os.stat_result:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise BuildError(f"required control file cannot be inspected: {path.name}") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or stat.S_IMODE(metadata.st_mode) not in allowed_modes
        or metadata.st_uid not in allowed_uids
        or not minimum_bytes <= metadata.st_size <= maximum_bytes
    ):
        raise BuildError(f"required control file has an unsafe contract: {path.name}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BuildError(f"required control file cannot be opened: {path.name}") from exc
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
            or opened.st_size != metadata.st_size
        ):
            raise BuildError(f"required control file changed during validation: {path.name}")
        return opened
    finally:
        os.close(descriptor)


def load_builder_config(
    path: Path,
    *,
    allowed_uids: set[int] | None = None,
) -> dict[str, object]:
    content = _secure_read(
        path,
        allowed_modes={0o400, 0o440},
        allowed_uids=allowed_uids or {0},
    )
    try:
        config = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildError("release builder configuration must be valid JSON") from exc
    if not isinstance(config, dict) or set(config) != CONFIG_FIELDS:
        raise BuildError("release builder configuration has unknown or missing fields")
    if config.get("schema_version") != 1:
        raise BuildError("release builder configuration schema must be 1")

    prefix = config.get("registry_prefix")
    allowed_hosts = config.get("allowed_registry_hosts")
    match = REGISTRY_PREFIX_PATTERN.fullmatch(str(prefix or ""))
    if (
        not match
        or not isinstance(allowed_hosts, list)
        or not allowed_hosts
        or any(not isinstance(host, str) for host in allowed_hosts)
        or match.group("host") not in allowed_hosts
        or match.group("host").split(":", 1)[0] in FORBIDDEN_REGISTRY_HOSTS
        or any(host.split(":", 1)[0] in FORBIDDEN_REGISTRY_HOSTS for host in allowed_hosts)
    ):
        raise BuildError("release registry is not an explicitly allowed private registry")

    base_images = config.get("base_images")
    if not isinstance(base_images, dict) or set(base_images) != {"backend", "frontend"}:
        raise BuildError("base_images must define backend and frontend")
    for image in base_images.values():
        image_match = BASE_IMAGE_PATTERN.fullmatch(str(image or ""))
        if not image_match or image_match.group("host") not in allowed_hosts:
            raise BuildError("every base image must use an allowed private digest reference")

    package_mirrors = config.get("package_mirrors")
    package_hosts = config.get("allowed_package_hosts")
    if (
        not isinstance(package_mirrors, dict)
        or set(package_mirrors) != {"python", "npm"}
        or not isinstance(package_hosts, list)
        or not package_hosts
        or any(not isinstance(host, str) or not host for host in package_hosts)
        or any(host in FORBIDDEN_PACKAGE_HOSTS for host in package_hosts)
    ):
        raise BuildError("package mirror allowlist is invalid")
    for mirror in package_mirrors.values():
        parsed_mirror = urlsplit(str(mirror or ""))
        if (
            parsed_mirror.scheme != "https"
            or not parsed_mirror.hostname
            or parsed_mirror.hostname not in package_hosts
            or parsed_mirror.hostname in FORBIDDEN_PACKAGE_HOSTS
            or parsed_mirror.username
            or parsed_mirror.password
            or parsed_mirror.query
            or parsed_mirror.fragment
        ):
            raise BuildError("every package mirror must use an allowed internal HTTPS host")

    address = config.get("openbao_address")
    parsed_address = urlsplit(str(address or ""))
    if parsed_address.scheme != "https" or not parsed_address.hostname:
        raise BuildError("OpenBao address must be an absolute HTTPS URL")
    transit_key = str(config.get("openbao_transit_key") or "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", transit_key):
        raise BuildError("OpenBao transit key name is invalid")
    for field in (
        "evidence_root",
        "openbao_token_file",
        "cosign_public_key",
        "trivy_cache_dir",
    ):
        value = config.get(field)
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise BuildError(f"{field} must be an absolute path")
    maximum_db_age = config.get("trivy_db_max_age_hours")
    if not isinstance(maximum_db_age, int) or not 1 <= maximum_db_age <= 72:
        raise BuildError("trivy_db_max_age_hours must be between 1 and 72")
    required_tools = config.get("required_tools")
    if not isinstance(required_tools, dict) or set(required_tools) != {"cosign", "syft", "trivy"}:
        raise BuildError("required_tools must pin cosign, syft and trivy")
    if any(not isinstance(value, str) or not value for value in required_tools.values()):
        raise BuildError("every release tool must have an exact required version")
    return config


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
    capture: bool = False,
) -> str:
    try:
        # No shell is used; every argv entry originates from fixed release controls.
        result = subprocess.run(  # nosec B603
            command,
            cwd=cwd,
            env=environment,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3600,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BuildError(f"release command could not complete: {command[0]}") from exc
    if result.returncode:
        raise BuildError(f"release command failed: {command[0]}")
    return result.stdout.strip() if capture else ""


def _ensure_evidence_directory(root: Path, commit: str, invocation: str) -> Path:
    try:
        metadata = root.lstat()
    except OSError as exc:
        raise BuildError("evidence root cannot be inspected") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or root.is_symlink()
        or metadata.st_uid not in {0, os.geteuid()}
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise BuildError("evidence root must be an owner-only non-symlink directory")
    output = root / f"{commit}-{invocation}"
    output.mkdir(mode=0o700, exist_ok=False)
    return output


def _validate_trivy_cache(
    cache: Path,
    *,
    maximum_age_hours: int,
    allowed_uids: set[int] | None = None,
    now: datetime | None = None,
) -> None:
    owners = allowed_uids or {0}
    try:
        metadata = cache.lstat()
    except OSError as exc:
        raise BuildError("Trivy cache cannot be inspected") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or cache.is_symlink()
        or metadata.st_uid not in owners
        or stat.S_IMODE(metadata.st_mode) not in {0o700, 0o750}
    ):
        raise BuildError("Trivy cache directory has an unsafe contract")
    database = cache / "db" / "trivy.db"
    metadata_path = cache / "db" / "metadata.json"
    _secure_file_metadata(
        database,
        allowed_modes={0o400, 0o440, 0o444},
        allowed_uids=owners,
        minimum_bytes=1024,
        maximum_bytes=1024 * 1024 * 1024,
    )
    try:
        db_metadata = json.loads(
            _secure_read(
                metadata_path,
                allowed_modes={0o400, 0o440, 0o444},
                allowed_uids=owners,
                maximum_bytes=16 * 1024,
            )
        )
        updated_at = datetime.fromisoformat(str(db_metadata["UpdatedAt"]).replace("Z", "+00:00"))
        next_update = datetime.fromisoformat(str(db_metadata["NextUpdate"]).replace("Z", "+00:00"))
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise BuildError("Trivy vulnerability database metadata is invalid") from exc
    current = now or datetime.now(UTC)
    maximum_age_seconds = maximum_age_hours * 60 * 60
    if (
        updated_at.tzinfo is None
        or next_update.tzinfo is None
        or updated_at > current
        or (current - updated_at).total_seconds() > maximum_age_seconds
        or next_update < current
    ):
        raise BuildError("Trivy vulnerability database is stale")


def _write_json(path: Path, payload: object) -> None:
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        written = 0
        while written < len(encoded):
            count = os.write(descriptor, encoded[written:])
            if count <= 0:
                raise BuildError("evidence file write did not complete")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _seal_evidence_file(path: Path) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise BuildError(f"expected evidence file is unavailable: {path.name}") from exc
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink() or metadata.st_uid != os.geteuid():
        raise BuildError(f"evidence file has an unsafe type or owner: {path.name}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise BuildError(f"evidence file cannot be opened safely: {path.name}") from exc
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
        ):
            raise BuildError(f"evidence file changed during validation: {path.name}")
        os.fchmod(descriptor, 0o600)
    except OSError as exc:
        raise BuildError(f"evidence file permissions cannot be sealed: {path.name}") from exc
    finally:
        os.close(descriptor)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_tool_versions(config: dict[str, object], repository: Path) -> dict[str, str]:
    required = config["required_tools"]
    if not isinstance(required, dict):
        raise BuildError("required tool contract is unavailable")
    commands = {
        "cosign": ["cosign", "version"],
        "syft": ["syft", "version"],
        "trivy": ["trivy", "version"],
    }
    actual: dict[str, str] = {}
    for tool, command in commands.items():
        output = _run(command, cwd=repository, capture=True)
        expected = str(required[tool])
        if expected not in output:
            raise BuildError(f"{tool} version does not match the approved builder contract")
        actual[tool] = expected
    return actual


def _build_component(
    *,
    component: str,
    dockerfile: str,
    repository: Path,
    evidence: Path,
    registry_prefix: str,
    commit: str,
    invocation: str,
    started_at: str,
    tools: dict[str, str],
    signing_environment: dict[str, str],
    public_key: Path,
    transit_key: str,
    build_arguments: dict[str, str],
    trivy_cache: Path,
) -> dict[str, str]:
    metadata_path = evidence / f"{component}-build-metadata.json"
    sbom_path = evidence / f"{component}.cdx.json"
    scan_path = evidence / f"{component}.trivy.json"
    provenance_path = evidence / f"{component}.provenance.json"
    tagged_image = f"{registry_prefix}/{component}:git-{commit}"
    build_command = [
        "docker",
        "buildx",
        "build",
        "--platform",
        "linux/amd64",
        "--provenance=false",
        "--sbom=false",
        "--push",
        "--metadata-file",
        str(metadata_path),
        "--tag",
        tagged_image,
        "--file",
        dockerfile,
    ]
    for name, value in sorted(build_arguments.items()):
        build_command.extend(["--build-arg", f"{name}={value}"])
    build_command.append(".")
    _run(build_command, cwd=repository)
    _seal_evidence_file(metadata_path)
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        digest = metadata["containerimage.digest"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise BuildError(f"{component} build did not produce an immutable digest") from exc
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise BuildError(f"{component} build digest is invalid")
    image = f"{registry_prefix}/{component}@{digest}"

    _run(["syft", "scan", image, "-o", f"cyclonedx-json={sbom_path}"], cwd=repository)
    _run(
        [
            "trivy",
            "--cache-dir",
            str(trivy_cache),
            "image",
            "--skip-db-update",
            "--skip-java-db-update",
            "--skip-check-update",
            "--offline-scan",
            "--format",
            "json",
            "--output",
            str(scan_path),
            "--exit-code",
            "1",
            "--ignore-unfixed=false",
            "--vuln-type",
            "os,library",
            "--severity",
            "HIGH,CRITICAL",
            image,
        ],
        cwd=repository,
    )
    _seal_evidence_file(sbom_path)
    _seal_evidence_file(scan_path)
    finished_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    _write_json(
        provenance_path,
        {
            "buildDefinition": {
                "buildType": "https://complywithai.de/build-types/hetzner-buildx/v1",
                "externalParameters": {
                    "component": component,
                    "dockerfile": dockerfile,
                    "platform": "linux/amd64",
                },
                "internalParameters": {},
                "resolvedDependencies": [
                    {
                        "uri": "git+https://github.com/Luyzz22/Compliance-Hub",
                        "digest": {"gitCommit": commit},
                    }
                ],
            },
            "runDetails": {
                "builder": {
                    "id": "https://complywithai.de/builders/hetzner-sovereign-release/v1",
                    "version": tools,
                },
                "metadata": {
                    "invocationId": invocation,
                    "startedOn": started_at,
                    "finishedOn": finished_at,
                },
            },
        },
    )
    kms_key = f"openbao://{transit_key}"
    _run(
        [
            "cosign",
            "sign",
            "--yes",
            "--tlog-upload=false",
            "--use-signing-config=false",
            "--key",
            kms_key,
            image,
        ],
        cwd=repository,
        environment=signing_environment,
    )
    for predicate_type, predicate in (
        ("slsaprovenance1", provenance_path),
        ("cyclonedx", sbom_path),
    ):
        _run(
            [
                "cosign",
                "attest",
                "--yes",
                "--tlog-upload=false",
                "--use-signing-config=false",
                "--type",
                predicate_type,
                "--predicate",
                str(predicate),
                "--key",
                kms_key,
                image,
            ],
            cwd=repository,
            environment=signing_environment,
        )
    for command in (
        ["cosign", "verify", "--private-infrastructure", "--key", str(public_key), image],
        [
            "cosign",
            "verify-attestation",
            "--private-infrastructure",
            "--type",
            "slsaprovenance1",
            "--key",
            str(public_key),
            image,
        ],
        [
            "cosign",
            "verify-attestation",
            "--private-infrastructure",
            "--type",
            "cyclonedx",
            "--key",
            str(public_key),
            image,
        ],
    ):
        _run(command, cwd=repository)
    return {
        "image": image,
        "sbom_sha256": _sha256(sbom_path),
        "scan_sha256": _sha256(scan_path),
        "provenance_sha256": _sha256(provenance_path),
    }


def main() -> int:
    os.umask(0o077)
    repository = Path(__file__).resolve().parents[1]
    config_path = Path(os.environ.get("COMPLIANCEHUB_RELEASE_BUILDER_CONFIG", ""))
    commit = os.environ.get("COMPLIANCEHUB_RELEASE_COMMIT", "")
    invocation = os.environ.get("COMPLIANCEHUB_RELEASE_INVOCATION", "")
    if not config_path.is_absolute():
        raise BuildError("COMPLIANCEHUB_RELEASE_BUILDER_CONFIG must be an absolute path")
    if not SHA_PATTERN.fullmatch(commit):
        raise BuildError("COMPLIANCEHUB_RELEASE_COMMIT must be a full lowercase Git SHA")
    if not INVOCATION_PATTERN.fullmatch(invocation):
        raise BuildError("COMPLIANCEHUB_RELEASE_INVOCATION is invalid")
    head = _run(["git", "rev-parse", "HEAD"], cwd=repository, capture=True)
    dirty = _run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=repository,
        capture=True,
    )
    if head != commit or dirty:
        raise BuildError("release checkout must match the clean approved commit")

    config = load_builder_config(config_path)
    token_path = Path(str(config["openbao_token_file"]))
    token = (
        _secure_read(
            token_path,
            allowed_modes={0o400, 0o600},
            allowed_uids={0, os.geteuid()},
            maximum_bytes=8 * 1024,
        )
        .decode("utf-8")
        .strip()
    )
    if len(token) < 20 or "\n" in token or "\r" in token:
        raise BuildError("OpenBao token file does not contain one valid short-lived token")
    public_key = Path(str(config["cosign_public_key"]))
    _secure_read(
        public_key,
        allowed_modes={0o400, 0o440, 0o444},
        allowed_uids={0},
    )
    tools = _check_tool_versions(config, repository)
    trivy_cache = Path(str(config["trivy_cache_dir"]))
    _validate_trivy_cache(
        trivy_cache,
        maximum_age_hours=int(config["trivy_db_max_age_hours"]),
    )
    evidence = _ensure_evidence_directory(Path(str(config["evidence_root"])), commit, invocation)
    signing_environment = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/nonexistent"),
        "BAO_ADDR": str(config["openbao_address"]),
        "BAO_TOKEN": token,
    }
    started_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    components: dict[str, dict[str, str]] = {}
    base_images = config["base_images"]
    package_mirrors = config["package_mirrors"]
    if not isinstance(base_images, dict) or not isinstance(package_mirrors, dict):
        raise BuildError("approved dependency mirrors are unavailable")
    for component, dockerfile, build_arguments in (
        (
            "backend",
            "Dockerfile.hetzner",
            {
                "PYTHON_BASE_IMAGE": str(base_images["backend"]),
                "PYTHON_INDEX_URL": str(package_mirrors["python"]),
            },
        ),
        (
            "frontend",
            "frontend/Dockerfile.hetzner",
            {
                "NODE_BASE_IMAGE": str(base_images["frontend"]),
                "NPM_REGISTRY_URL": str(package_mirrors["npm"]),
            },
        ),
    ):
        components[component] = _build_component(
            component=component,
            dockerfile=dockerfile,
            repository=repository,
            evidence=evidence,
            registry_prefix=str(config["registry_prefix"]),
            commit=commit,
            invocation=invocation,
            started_at=started_at,
            tools=tools,
            signing_environment=signing_environment,
            public_key=public_key,
            transit_key=str(config["openbao_transit_key"]),
            build_arguments=build_arguments,
            trivy_cache=trivy_cache,
        )
    _write_json(
        evidence / "build-manifest.json",
        {
            "schema_version": 1,
            "commit_sha": commit,
            "invocation_id": invocation,
            "builder_id": "https://complywithai.de/builders/hetzner-sovereign-release/v1",
            "tools": tools,
            "components": components,
        },
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"sovereign_release_build=failed: {exc}", file=os.sys.stderr)
        raise SystemExit(1) from exc
