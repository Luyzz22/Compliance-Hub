#!/usr/bin/env python3
"""Fail-closed host preflight for the private synthetic Hetzner demonstration."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import os
import re
import stat
import subprocess  # nosec B404
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

# subprocess is limited below to fixed argument vectors; shell execution is never enabled.

BASE = Path(__file__).resolve().parent
GUID = re.compile(r"^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$", re.IGNORECASE)
SHA = re.compile(r"^[0-9a-f]{40}$")
OPAQUE = re.compile(r"^[A-Za-z0-9_-]+$")

SECRET_CONTRACT: dict[str, tuple[int, int, str]] = {
    "synthetic-demo-tls-certificate.pem": (65532, 256, "pem"),
    "synthetic-demo-tls-private-key.pem": (65532, 256, "private_key"),
    "synthetic-demo-postgres-admin-password": (70, 32, "opaque"),
    "synthetic-demo-postgres-backend-password": (70, 32, "opaque"),
    "synthetic-demo-postgres-frontend-password": (10001, 32, "opaque"),
    "synthetic-demo-postgres-server-certificate.pem": (70, 256, "pem"),
    "synthetic-demo-postgres-server-private-key.pem": (70, 256, "private_key"),
    "synthetic-demo-postgres-ca-app.pem": (10001, 256, "pem"),
    "synthetic-demo-postgres-ca-policy.pem": (70, 256, "pem"),
    "synthetic-demo-backend-database-url": (10001, 32, "postgres_dsn"),
    "synthetic-demo-s3-access-key": (10001, 16, "opaque"),
    "synthetic-demo-s3-secret-access-key": (10001, 32, "opaque"),
    "synthetic-demo-azure-openai-client-certificate.pem": (10001, 512, "pem_private"),
    "synthetic-demo-bff-shared-secret": (10001, 32, "opaque"),
    "synthetic-demo-audit-pseudonymization-key": (10001, 32, "opaque"),
    "synthetic-demo-credential-pepper": (10001, 32, "opaque"),
    "synthetic-demo-mfa-encryption-key": (10001, 32, "opaque"),
    "synthetic-demo-internal-health-api-key": (10001, 32, "opaque"),
    "synthetic-demo-auth-transaction-secret": (10001, 32, "opaque"),
    "synthetic-demo-lead-admin-secret": (10001, 32, "opaque"),
    "synthetic-demo-operator-password": (10001, 16, "password"),
}


class PreflightError(RuntimeError):
    pass


def _read_descriptor(descriptor: int, maximum: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while total <= maximum:
        chunk = os.read(descriptor, min(64 * 1024, maximum + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    content = b"".join(chunks)
    if len(content) > maximum:
        raise PreflightError("protected file exceeds its maximum size")
    return content


def _load_env(path: Path) -> dict[str, str]:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise PreflightError("environment file must be a regular non-symlink file")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise PreflightError("environment file must use mode 0600")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
            or opened.st_size != metadata.st_size
            or stat.S_IMODE(opened.st_mode) != 0o600
        ):
            raise PreflightError("environment file changed during validation")
        raw_environment = _read_descriptor(descriptor, 1024 * 1024)
        final = os.fstat(descriptor)
        if (
            len(raw_environment) != opened.st_size
            or final.st_dev != opened.st_dev
            or final.st_ino != opened.st_ino
            or final.st_size != opened.st_size
            or stat.S_IMODE(final.st_mode) != 0o600
        ):
            raise PreflightError("environment file changed during secure read")
    finally:
        os.close(descriptor)
    values: dict[str, str] = {}
    for number, raw in enumerate(raw_environment.decode("utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise PreflightError(f"environment line {number} is not KEY=VALUE")
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or key in values:
            raise PreflightError(f"environment line {number} has an invalid or duplicate key")
        if any(character in value for character in "\r\n\x00"):
            raise PreflightError(f"environment value {key} contains control characters")
        values[key] = value.strip()
    return values


def _require(values: dict[str, str], key: str, expected: str | None = None) -> str:
    value = values.get(key, "").strip()
    if not value:
        raise PreflightError(f"{key} is required")
    if expected is not None and value != expected:
        raise PreflightError(f"{key} must be {expected}")
    return value


def _validate_environment(values: dict[str, str]) -> None:
    for key, expected in {
        "COMPLIANCEHUB_RELEASE_CHANNEL": "pilot",
        "COMPLIANCEHUB_RELEASE_PROFILE": "synthetic_demo",
        "COMPLIANCEHUB_SOVEREIGNTY_MODE": "standard_dach",
        "COMPLIANCEHUB_FEATURE_DEMO_MODE": "true",
        "COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS": "true",
        "COMPLIANCEHUB_DEMO_AZURE_INFERENCE_ENABLED": "true",
        "COMPLIANCEHUB_DEMO_SYNTHETIC_ONLY_ATTESTED": "true",
        "COMPLIANCEHUB_FEATURE_LLM_ENABLED": "true",
        "COMPLIANCEHUB_FEATURE_LLM_CHAT_ASSISTANT": "true",
        "COMPLIANCEHUB_LLM_PREFER_AZURE": "true",
        "COMPLIANCEHUB_LLM_ASSUME_AZURE_EU": "true",
        "COMPLIANCEHUB_LLM_PII_MODE": "block",
        "COMPLIANCEHUB_ENTRA_ENABLED": "false",
        "COMPLIANCEHUB_SELF_REGISTRATION_ENABLED": "false",
        "COMPLIANCEHUB_PUBLIC_DEMO_ENABLED": "false",
        "COMPLIANCEHUB_RUNTIME_STORAGE_BACKEND": "s3",
        "COMPLIANCEHUB_RELATIONAL_RUNTIME_BACKEND": "postgres",
        "POSTGRES_HOST": "postgres",
        "POSTGRES_USER": "compliancehub_frontend",
        "COMPLIANCEHUB_LEGAL_PUBLISH_READY": "false",
    }.items():
        _require(values, key, expected)
    enabled_literal = str(True).lower()
    _require(values, "COMPLIANCEHUB_PASSWORD_LOGIN_ENABLED", enabled_literal)

    host = _require(values, "COMPLIANCEHUB_PUBLIC_HOST")
    if host != host.lower() or not re.fullmatch(r"[a-z0-9.-]+", host):
        raise PreflightError("COMPLIANCEHUB_PUBLIC_HOST must be a normalized DNS host")
    if _require(values, "COMPLIANCEHUB_APP_ORIGIN") != f"https://{host}":
        raise PreflightError("COMPLIANCEHUB_APP_ORIGIN must match the public HTTPS host")
    if host not in _require(values, "COMPLIANCEHUB_TRUSTED_HOSTS").split(","):
        raise PreflightError("COMPLIANCEHUB_TRUSTED_HOSTS must include the public host")

    network = ipaddress.ip_network(_require(values, "COMPLIANCEHUB_DEMO_ALLOWED_CIDR"))
    if network.prefixlen == 0 or network.num_addresses > 256:
        raise PreflightError("COMPLIANCEHUB_DEMO_ALLOWED_CIDR is broader than the demo policy")

    endpoint = urlsplit(_require(values, "AZURE_OPENAI_ENDPOINT"))
    if endpoint.scheme != "https" or not (endpoint.hostname or "").endswith(".openai.azure.com"):
        raise PreflightError("AZURE_OPENAI_ENDPOINT must be an Azure OpenAI HTTPS origin")
    if endpoint.path not in {"", "/"} or endpoint.query or endpoint.fragment:
        raise PreflightError("AZURE_OPENAI_ENDPOINT must be a bare origin")
    for key in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID"):
        value = _require(values, key)
        if not GUID.fullmatch(value) or value == "00000000-0000-0000-0000-000000000000":
            raise PreflightError(f"{key} must be a non-placeholder GUID")
    if not _require(values, "AZURE_OPENAI_DEPLOYMENT"):
        raise PreflightError("AZURE_OPENAI_DEPLOYMENT is required")

    s3 = urlsplit(_require(values, "COMPLIANCEHUB_S3_ENDPOINT"))
    if s3.scheme != "https" or s3.hostname != "nbg1.your-objectstorage.com":
        raise PreflightError("synthetic demo S3 endpoint must be Hetzner NBG1 over HTTPS")
    if _require(values, "COMPLIANCEHUB_S3_REGION") != "nbg1":
        raise PreflightError("synthetic demo S3 region must be nbg1")
    bucket = _require(values, "COMPLIANCEHUB_S3_BUCKET")
    if "replace" in bucket.lower() or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        raise PreflightError("COMPLIANCEHUB_S3_BUCKET must be a real private bucket name")

    if not SHA.fullmatch(_require(values, "COMPLIANCEHUB_RELEASE_COMMIT")):
        raise PreflightError("COMPLIANCEHUB_RELEASE_COMMIT must be a full Git commit")
    for key in ("COMPLIANCEHUB_BACKEND_IMAGE", "COMPLIANCEHUB_FRONTEND_IMAGE"):
        value = _require(values, key)
        if value.endswith(":synthetic-demo") or "replace" in value.lower():
            raise PreflightError(f"{key} must use a release-specific immutable local tag")

    forbidden_keys = {
        "AZURE_OPENAI_API_KEY",
        "COMPLIANCEHUB_DB_URL",
        "POSTGRES_PASSWORD",
        "NEXT_PUBLIC_API_KEY",
        "COMPLIANCEHUB_API_KEYS",
    }
    exposed = sorted(key for key in forbidden_keys if values.get(key, "").strip())
    if exposed:
        raise PreflightError(
            "direct secret environment variables are forbidden: " + ", ".join(exposed)
        )
    forbidden_vendors = ("vercel", "neon.tech", "supabase", "posthog.com", "sentry.io")
    for key, value in values.items():
        if any(vendor in value.lower() for vendor in forbidden_vendors):
            raise PreflightError(f"{key} contains a forbidden runtime provider")


def _read_secret(path: Path, *, minimum: int, kind: str) -> str:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise PreflightError(f"{path.name} must be a regular non-symlink file")
    expected_uid = SECRET_CONTRACT[path.name][0]
    if metadata.st_uid != expected_uid:
        raise PreflightError(f"{path.name} must be owned by numeric UID {expected_uid}")
    if stat.S_IMODE(metadata.st_mode) != 0o400:
        raise PreflightError(f"{path.name} must use mode 0400")
    if metadata.st_size < minimum or metadata.st_size > 1024 * 1024:
        raise PreflightError(f"{path.name} has an invalid size")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(descriptor)
        if (
            opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
            or opened.st_uid != expected_uid
            or opened.st_size != metadata.st_size
            or stat.S_IMODE(opened.st_mode) != 0o400
        ):
            raise PreflightError(f"{path.name} changed during secure validation")
        content = _read_descriptor(descriptor, 1024 * 1024)
        final = os.fstat(descriptor)
        if (
            len(content) != opened.st_size
            or final.st_dev != opened.st_dev
            or final.st_ino != opened.st_ino
            or final.st_uid != expected_uid
            or final.st_size != opened.st_size
            or stat.S_IMODE(final.st_mode) != 0o400
        ):
            raise PreflightError(f"{path.name} changed during secure read")
    finally:
        os.close(descriptor)
    value = content.decode("utf-8").strip()
    if kind == "opaque" and (not OPAQUE.fullmatch(value) or len(value) < minimum):
        raise PreflightError(f"{path.name} has an invalid opaque-secret format")
    if kind == "password":
        password_classes = (
            any(character.isupper() for character in value),
            any(character.islower() for character in value),
            any(character.isdigit() for character in value),
        )
        if len(value) < minimum or not all(password_classes):
            raise PreflightError(f"{path.name} does not satisfy the demo password policy")
    if kind == "pem" and "-----BEGIN CERTIFICATE-----" not in value:
        raise PreflightError(f"{path.name} is not a PEM certificate")
    if kind == "private_key" and "PRIVATE KEY-----" not in value:
        raise PreflightError(f"{path.name} is not a PEM private key")
    if kind == "pem_private" and not (
        "-----BEGIN CERTIFICATE-----" in value and "PRIVATE KEY-----" in value
    ):
        raise PreflightError(f"{path.name} must contain a certificate and private key")
    return value


def _run_checked(arguments: list[str], *, input_text: str | None = None) -> str:
    # Executables are fixed by the caller and every variable path is validated first.
    completed = subprocess.run(  # nosec B603
        arguments,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if completed.returncode:
        raise PreflightError(f"command failed without disclosing output: {arguments[0]}")
    return completed.stdout.strip()


def _certificate_contract(secrets: Path, public_host: str) -> None:
    edge_cert = secrets / "synthetic-demo-tls-certificate.pem"
    edge_key = secrets / "synthetic-demo-tls-private-key.pem"
    pg_cert = secrets / "synthetic-demo-postgres-server-certificate.pem"
    pg_key = secrets / "synthetic-demo-postgres-server-private-key.pem"
    pg_ca = secrets / "synthetic-demo-postgres-ca-policy.pem"

    for certificate in (edge_cert, pg_cert):
        _run_checked(["openssl", "x509", "-in", str(certificate), "-noout", "-checkend", "604800"])
    _run_checked(["openssl", "x509", "-in", str(edge_cert), "-noout", "-checkhost", public_host])
    _run_checked(["openssl", "x509", "-in", str(pg_cert), "-noout", "-checkhost", "postgres"])
    _run_checked(["openssl", "verify", "-CAfile", str(pg_ca), str(pg_cert)])

    for certificate, private_key in ((edge_cert, edge_key), (pg_cert, pg_key)):
        cert_public = _run_checked(
            ["openssl", "x509", "-in", str(certificate), "-pubkey", "-noout"]
        )
        key_public = _run_checked(["openssl", "pkey", "-in", str(private_key), "-pubout"])
        if (
            hashlib.sha256(cert_public.encode()).digest()
            != hashlib.sha256(key_public.encode()).digest()
        ):
            raise PreflightError(f"{certificate.name} does not match its private key")


def _database_contract(secrets: Path) -> None:
    dsn = _read_secret(
        secrets / "synthetic-demo-backend-database-url", minimum=32, kind="postgres_dsn"
    )
    parsed = urlsplit(dsn)
    if parsed.scheme != "postgresql+psycopg" or parsed.hostname != "postgres":
        raise PreflightError("backend database URL must use psycopg and the private postgres host")
    if unquote(parsed.username or "") != "compliancehub_backend":
        raise PreflightError("backend database URL must use the least-privileged backend role")
    backend_password = _read_secret(
        secrets / "synthetic-demo-postgres-backend-password", minimum=32, kind="opaque"
    )
    if unquote(parsed.password or "") != backend_password:
        raise PreflightError("backend database URL password does not match its source secret")
    query = parse_qs(parsed.query)
    if query.get("sslmode") != ["verify-full"]:
        raise PreflightError("backend database URL must use sslmode=verify-full")
    if query.get("sslrootcert") != ["/run/secrets/postgres_ca_certificate"]:
        raise PreflightError("backend database URL must bind the mounted PostgreSQL trust anchor")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the synthetic Hetzner demo candidate")
    parser.add_argument("--env-file", default=".env.synthetic-demo")
    args = parser.parse_args()

    environment_candidate = BASE / args.env_file
    if environment_candidate.is_symlink():
        raise PreflightError("environment file must not be a symlink")
    environment_path = environment_candidate.resolve()
    if environment_path.parent != BASE:
        raise PreflightError("environment file must reside in the deployment directory")
    values = _load_env(environment_path)
    _validate_environment(values)

    secrets = BASE / "secrets"
    secret_dir_metadata = secrets.lstat()
    if not stat.S_ISDIR(secret_dir_metadata.st_mode) or secrets.is_symlink():
        raise PreflightError("secrets must be a real directory")
    if stat.S_IMODE(secret_dir_metadata.st_mode) != 0o700:
        raise PreflightError("secrets directory must use mode 0700")
    if secret_dir_metadata.st_uid not in {0, os.getuid()}:
        raise PreflightError("secrets directory must be owned by root or the deployment user")
    secret_values: dict[str, str] = {}
    for name, (_uid, minimum, kind) in SECRET_CONTRACT.items():
        secret_values[name] = _read_secret(secrets / name, minimum=minimum, kind=kind)

    if (
        secret_values["synthetic-demo-postgres-ca-app.pem"]
        != secret_values["synthetic-demo-postgres-ca-policy.pem"]
    ):
        raise PreflightError("PostgreSQL trust-anchor copies differ")
    _certificate_contract(secrets, _require(values, "COMPLIANCEHUB_PUBLIC_HOST"))
    _database_contract(secrets)

    _run_checked(
        [
            "docker",
            "compose",
            "--env-file",
            str(environment_path),
            "-f",
            str(BASE / "compose.synthetic-demo.yml"),
            "config",
            "--quiet",
        ]
    )
    print("synthetic_demo_preflight=passed secrets_disclosed=false production_ready=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, PreflightError) as error:
        print(f"synthetic_demo_preflight=failed reason={error}", file=sys.stderr)
        raise SystemExit(1) from None
