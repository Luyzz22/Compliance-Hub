#!/usr/bin/env python3
"""Fail-closed validation for a concrete Compliance Hub production release."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import re

# Fixed argv execution is required only to resolve the checked-out Git commit.
import subprocess  # nosec B404
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
IMAGE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:/-]*@sha256:([0-9a-f]{64})$")
PLACEHOLDER_PATTERN = re.compile(r"(?:replace-with|example\.invalid|^0+$|pending)", re.I)
BLUEPRINT_FILES = (
    "compose.yml",
    "Caddyfile",
    "../../infra/opa/policies/compliancehub/regos/action_policy.rego",
)
APPROVAL_FIELDS = ("security", "privacy", "operations", "product_owner")
SIGNATURE_ROLES = ("builder", "approver")
ROOT_FIELDS = {
    "schema_version",
    "release_id",
    "commit_sha",
    "created_at",
    "expires_at",
    "built_by",
    "approved_by",
    "change_ticket",
    "images",
    "sboms",
    "security",
    "deployment",
    "database",
    "rollback",
    "approvals",
    "signatures",
}


def _reject_unknown_fields(
    data: dict[str, Any], allowed: set[str], field: str, errors: list[str]
) -> None:
    for key in sorted(set(data) - allowed):
        errors.append(f"{field} contains unsupported field {key}")


def _parse_timestamp(value: object, field: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str):
        errors.append(f"{field} must be an RFC 3339 UTC timestamp")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be an RFC 3339 UTC timestamp")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        errors.append(f"{field} must use UTC")
        return None
    return parsed


def _mapping(value: object, field: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{field} must be an object")
        return {}
    return value


def _require_reviewed_text(data: dict[str, Any], field: str, errors: list[str]) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip() or PLACEHOLDER_PATTERN.search(value):
        errors.append(f"{field} must contain a reviewed non-placeholder value")
        return ""
    return value.strip()


def _require_digest(
    data: dict[str, Any], key: str, errors: list[str], *, label: str | None = None
) -> str:
    value = data.get(key)
    field = label or key
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value) or value == "0" * 64:
        errors.append(f"{field} must be a non-zero lowercase SHA-256 digest")
        return ""
    return value


def _require_image(
    data: dict[str, Any], key: str, errors: list[str], *, label: str | None = None
) -> str:
    value = data.get(key)
    field = label or key
    match = IMAGE_PATTERN.fullmatch(value) if isinstance(value, str) else None
    if not match or match.group(1) == "0" * 64 or PLACEHOLDER_PATTERN.search(value):
        errors.append(f"{field} must be an immutable non-placeholder image reference")
        return ""
    return value


def canonical_signing_payload(payload: object) -> bytes:
    """Return the deterministic release payload covered by both signatures."""

    if not isinstance(payload, dict):
        raise ValueError("release evidence must be an object")
    unsigned = {key: value for key, value in payload.items() if key != "signatures"}
    return json.dumps(
        unsigned,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _signature_entries(payload: object, errors: list[str]) -> dict[str, dict[str, Any]]:
    root = payload if isinstance(payload, dict) else {}
    raw_signatures = root.get("signatures")
    if not isinstance(raw_signatures, list):
        errors.append("signatures must be an array")
        return {}

    signatures: dict[str, dict[str, Any]] = {}
    for index, raw_signature in enumerate(raw_signatures):
        field = f"signatures[{index}]"
        if not isinstance(raw_signature, dict):
            errors.append(f"{field} must be an object")
            continue
        _reject_unknown_fields(
            raw_signature,
            {"role", "subject", "algorithm", "key_id", "signature"},
            field,
            errors,
        )
        role = raw_signature.get("role")
        if role not in SIGNATURE_ROLES:
            errors.append(f"{field}.role must be builder or approver")
            continue
        if role in signatures:
            errors.append(f"signatures must contain exactly one {role} signature")
            continue
        if raw_signature.get("algorithm") != "Ed25519":
            errors.append(f"{field}.algorithm must be Ed25519")
        subject = _require_reviewed_text(raw_signature, "subject", errors)
        expected_subject = root.get("built_by" if role == "builder" else "approved_by")
        if subject and subject != expected_subject:
            errors.append(f"{field}.subject must match {role} identity")
        _require_digest(raw_signature, "key_id", errors, label=f"{field}.key_id")
        signature = raw_signature.get("signature")
        if not isinstance(signature, str) or PLACEHOLDER_PATTERN.search(signature):
            errors.append(f"{field}.signature must be non-placeholder base64")
        else:
            try:
                decoded = base64.b64decode(signature, validate=True)
            except (ValueError, binascii.Error):
                errors.append(f"{field}.signature must be valid base64")
            else:
                if len(decoded) != 64:
                    errors.append(f"{field}.signature must encode a 64-byte Ed25519 signature")
        signatures[role] = raw_signature

    for role in SIGNATURE_ROLES:
        if role not in signatures:
            errors.append(f"signatures must contain exactly one {role} signature")
    if len(raw_signatures) != len(SIGNATURE_ROLES):
        errors.append("signatures must contain exactly two entries")
    builder_id = signatures.get("builder", {}).get("key_id")
    approver_id = signatures.get("approver", {}).get("key_id")
    if builder_id and approver_id and builder_id == approver_id:
        errors.append("builder and approver key_id values must differ")
    return signatures


def verify_release_signatures(
    payload: object,
    *,
    builder_public_key: object,
    approver_public_key: object,
) -> list[str]:
    """Verify independent Ed25519 signatures against externally trusted keys."""

    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    errors: list[str] = []
    signatures = _signature_entries(payload, errors)
    if errors:
        return errors
    if not isinstance(builder_public_key, Ed25519PublicKey):
        errors.append("trusted builder public key must be Ed25519")
    if not isinstance(approver_public_key, Ed25519PublicKey):
        errors.append("trusted approver public key must be Ed25519")
    if errors:
        return errors

    builder_raw = builder_public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    approver_raw = approver_public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    if builder_raw == approver_raw:
        return ["trusted builder and approver public keys must differ"]

    message = canonical_signing_payload(payload)
    for role, public_key, raw_key in (
        ("builder", builder_public_key, builder_raw),
        ("approver", approver_public_key, approver_raw),
    ):
        expected_key_id = hashlib.sha256(raw_key).hexdigest()
        if signatures[role]["key_id"] != expected_key_id:
            errors.append(f"{role} key_id does not match the trusted public key")
            continue
        encoded_signature = signatures[role]["signature"]
        try:
            public_key.verify(base64.b64decode(encoded_signature, validate=True), message)
        except (InvalidSignature, ValueError):
            errors.append(f"{role} Ed25519 signature is invalid")
    return errors


def _load_ed25519_public_key(path: Path, label: str, errors: list[str]) -> object | None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except (OSError, ValueError, TypeError):
        errors.append(f"{label} public key cannot be read as PEM")
        return None
    if not isinstance(key, Ed25519PublicKey):
        errors.append(f"{label} public key must be Ed25519")
        return None
    return key


def _sha256_file(path: Path, label: str, errors: list[str]) -> str:
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        errors.append(f"{label} cannot be read")
        return ""
    return digest


def validate_cyclonedx_sbom(path: Path, label: str) -> list[str]:
    """Reject empty, malformed or mislabeled SBOM artifacts."""

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return [f"{label} must be readable JSON without duplicate keys"]
    if not isinstance(payload, dict):
        return [f"{label} must be a CycloneDX JSON object"]

    errors: list[str] = []
    if payload.get("bomFormat") != "CycloneDX":
        errors.append(f"{label}.bomFormat must be CycloneDX")
    if payload.get("specVersion") not in {"1.4", "1.5", "1.6", "1.7"}:
        errors.append(f"{label}.specVersion must be a supported CycloneDX version")
    version = payload.get("version")
    if type(version) is not int or version < 1:
        errors.append(f"{label}.version must be a positive integer")
    components = payload.get("components")
    if not isinstance(components, list) or not components:
        errors.append(f"{label}.components must be a non-empty array")
    else:
        for index, component in enumerate(components):
            if not isinstance(component, dict):
                errors.append(f"{label}.components[{index}] must be an object")
                continue
            for field in ("name", "type", "version"):
                value = component.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{label}.components[{index}].{field} must be non-empty text")
    return errors


def validate_restore_drill_evidence(
    path: Path,
    *,
    release_created_at: datetime | None = None,
) -> list[str]:
    """Validate the measured, cleaned-up PostgreSQL and object restore drill."""

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return ["restore drill evidence must be readable JSON without duplicate keys"]
    errors: list[str] = []
    root = _mapping(payload, "restore drill evidence", errors)
    _reject_unknown_fields(
        root,
        {
            "schema_version",
            "drill_id",
            "started_at",
            "completed_at",
            "tools",
            "postgres",
            "object_storage",
            "recovery",
        },
        "restore drill evidence",
        errors,
    )
    if type(root.get("schema_version")) is not int or root.get("schema_version") != 1:
        errors.append("restore drill evidence.schema_version must be 1")
    drill_id = root.get("drill_id")
    if not isinstance(drill_id, str) or not re.fullmatch(r"DR-[0-9]{8}-[A-Z0-9]{4,16}", drill_id):
        errors.append("restore drill evidence.drill_id is invalid")
    started = _parse_timestamp(root.get("started_at"), "restore drill started_at", errors)
    completed = _parse_timestamp(root.get("completed_at"), "restore drill completed_at", errors)
    if started and completed and completed <= started:
        errors.append("restore drill completed_at must be later than started_at")
    if completed and release_created_at:
        if completed > release_created_at:
            errors.append("restore drill must complete before release evidence is created")
        if release_created_at - completed > timedelta(days=31):
            errors.append("restore drill evidence must be no older than 31 days")

    tools = _mapping(root.get("tools"), "restore drill tools", errors)
    _reject_unknown_fields(
        tools,
        {"psql", "pg_restore", "createdb", "dropdb", "rclone"},
        "restore drill tools",
        errors,
    )
    for tool in ("psql", "pg_restore", "createdb", "dropdb", "rclone"):
        _require_reviewed_text(tools, tool, errors)

    postgres = _mapping(root.get("postgres"), "restore drill postgres", errors)
    _reject_unknown_fields(
        postgres,
        {
            "status",
            "public_table_count",
            "required_tables",
            "restore_seconds",
            "cleanup_status",
            "backup_sha256",
            "backup_created_at",
            "restore_host_sha256",
        },
        "restore drill postgres",
        errors,
    )
    for field in ("status", "cleanup_status"):
        if postgres.get(field) != "passed":
            errors.append(f"restore drill postgres.{field} must be passed")
    if (
        type(postgres.get("public_table_count")) is not int
        or postgres.get("public_table_count", 0) < 1
    ):
        errors.append("restore drill postgres.public_table_count must be positive")
    required_tables = postgres.get("required_tables")
    if (
        not isinstance(required_tables, list)
        or not required_tables
        or any(not isinstance(value, str) or not value for value in required_tables)
    ):
        errors.append("restore drill postgres.required_tables must be non-empty")
    for field in ("restore_seconds",):
        value = postgres.get(field)
        if type(value) not in {int, float} or value < 0:
            errors.append(f"restore drill postgres.{field} must be non-negative")
    for field in ("backup_sha256", "restore_host_sha256"):
        _require_digest(postgres, field, errors, label=f"restore drill postgres.{field}")
    postgres_backup_created = _parse_timestamp(
        postgres.get("backup_created_at"),
        "restore drill postgres.backup_created_at",
        errors,
    )

    storage = _mapping(root.get("object_storage"), "restore drill object_storage", errors)
    _reject_unknown_fields(
        storage,
        {
            "status",
            "object_count",
            "total_bytes",
            "verified_object_count",
            "restore_seconds",
            "cleanup_status",
            "backup_reference_sha256",
            "backup_created_at",
            "endpoint_host_sha256",
        },
        "restore drill object_storage",
        errors,
    )
    for field in ("status", "cleanup_status"):
        if storage.get(field) != "passed":
            errors.append(f"restore drill object_storage.{field} must be passed")
    object_count = storage.get("object_count")
    verified_count = storage.get("verified_object_count")
    if type(object_count) is not int or object_count < 1:
        errors.append("restore drill object_storage.object_count must be positive")
    if type(verified_count) is not int or verified_count != object_count:
        errors.append("restore drill object_storage.verified_object_count must match object_count")
    if type(storage.get("total_bytes")) is not int or storage.get("total_bytes", 0) < 1:
        errors.append("restore drill object_storage.total_bytes must be positive")
    if (
        type(storage.get("restore_seconds")) not in {int, float}
        or storage.get("restore_seconds", -1) < 0
    ):
        errors.append("restore drill object_storage.restore_seconds must be non-negative")
    for field in ("backup_reference_sha256", "endpoint_host_sha256"):
        _require_digest(storage, field, errors, label=f"restore drill object_storage.{field}")
    object_backup_created = _parse_timestamp(
        storage.get("backup_created_at"),
        "restore drill object_storage.backup_created_at",
        errors,
    )

    recovery = _mapping(root.get("recovery"), "restore drill recovery", errors)
    _reject_unknown_fields(
        recovery,
        {
            "status",
            "rpo_minutes",
            "rpo_target_minutes",
            "rto_seconds",
            "rto_target_seconds",
        },
        "restore drill recovery",
        errors,
    )
    if recovery.get("status") != "passed":
        errors.append("restore drill recovery.status must be passed")
    for actual, target in (
        ("rpo_minutes", "rpo_target_minutes"),
        ("rto_seconds", "rto_target_seconds"),
    ):
        actual_value = recovery.get(actual)
        target_value = recovery.get(target)
        if type(actual_value) not in {int, float} or actual_value < 0:
            errors.append(f"restore drill recovery.{actual} must be non-negative")
        if type(target_value) not in {int, float} or target_value <= 0:
            errors.append(f"restore drill recovery.{target} must be positive")
        if (
            type(actual_value) in {int, float}
            and type(target_value) in {int, float}
            and actual_value > target_value
        ):
            errors.append(f"restore drill recovery.{actual} exceeds {target}")
    if started and postgres_backup_created and postgres_backup_created > started:
        errors.append("restore drill postgres.backup_created_at cannot be later than started_at")
    if started and object_backup_created and object_backup_created > started:
        errors.append(
            "restore drill object_storage.backup_created_at cannot be later than started_at"
        )
    recorded_rpo = recovery.get("rpo_minutes")
    if (
        started
        and postgres_backup_created
        and object_backup_created
        and type(recorded_rpo)
        in {
            int,
            float,
        }
    ):
        calculated_rpo = (
            max(
                (started - postgres_backup_created).total_seconds(),
                (started - object_backup_created).total_seconds(),
            )
            / 60
        )
        if abs(float(recorded_rpo) - calculated_rpo) > 0.01:
            errors.append("restore drill recovery.rpo_minutes does not match backup timestamps")
    recorded_rto = recovery.get("rto_seconds")
    if started and completed and type(recorded_rto) in {int, float}:
        calculated_rto = (completed - started).total_seconds()
        if abs(float(recorded_rto) - calculated_rto) > 0.01:
            errors.append("restore drill recovery.rto_seconds does not match drill timestamps")
    if (
        isinstance(required_tables, list)
        and type(postgres.get("public_table_count")) is int
        and postgres["public_table_count"] < len(set(required_tables))
    ):
        errors.append(
            "restore drill postgres.public_table_count cannot be smaller than required_tables"
        )
    return errors


def read_environment(path: Path, errors: list[str]) -> dict[str, str]:
    environment: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        errors.append("deployment environment cannot be read")
        return environment
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            errors.append(f"deployment environment line {line_number} is malformed")
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", key):
            errors.append(f"deployment environment line {line_number} has an invalid key")
            continue
        if key in environment:
            errors.append(f"deployment environment contains duplicate key {key}")
            continue
        if any(character in value for character in ("'", '"', "$", "#", "\\")):
            errors.append(
                f"deployment environment {key} must use the approved literal dotenv subset"
            )
            continue
        environment[key] = value
    return environment


def canonical_environment_sha256(environment: dict[str, str]) -> str:
    """Hash the exact non-secret env contract without its circular evidence digest."""

    canonical = "".join(
        f"{key}={environment[key]}\n"
        for key in sorted(environment)
        if key != "COMPLIANCEHUB_RELEASE_EVIDENCE_SHA256"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def deployment_blueprint_sha256(deployment_directory: Path) -> str:
    """Hash immutable deployment policy/config files in a deterministic order."""

    deployment_root = deployment_directory.resolve(strict=True)
    repository_root = deployment_root.parent.parent
    digest = hashlib.sha256()
    for relative_path in BLUEPRINT_FILES:
        source_path = deployment_root / relative_path
        if source_path.is_symlink():
            raise OSError(f"deployment blueprint file is invalid: {relative_path}")
        path = source_path.resolve(strict=True)
        if not path.is_relative_to(repository_root) or not path.is_file():
            raise OSError(f"deployment blueprint file is invalid: {relative_path}")
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def validate_deployment_binding(
    payload: object,
    environment: dict[str, str],
    *,
    evidence_sha256: str,
) -> list[str]:
    """Bind the approved release to the exact environment consumed by Compose."""

    errors: list[str] = []
    root = payload if isinstance(payload, dict) else {}
    images = root.get("images") if isinstance(root.get("images"), dict) else {}
    deployment = root.get("deployment") if isinstance(root.get("deployment"), dict) else {}
    bindings = {
        "COMPLIANCEHUB_RELEASE_ID": root.get("release_id"),
        "COMPLIANCEHUB_RELEASE_COMMIT": root.get("commit_sha"),
        "COMPLIANCEHUB_BACKEND_IMAGE": images.get("backend"),
        "COMPLIANCEHUB_FRONTEND_IMAGE": images.get("frontend"),
        "COMPLIANCEHUB_RELEASE_EVIDENCE_SHA256": evidence_sha256,
        "COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256": deployment.get("blueprint_sha256"),
    }
    for key, expected in bindings.items():
        if environment.get(key) != expected:
            errors.append(f"deployment environment {key} does not match release evidence")
    if deployment.get("configuration_sha256") != canonical_environment_sha256(environment):
        errors.append("deployment environment does not match deployment.configuration_sha256")
    return errors


def validate_rollback_binding(
    payload: object,
    environment: dict[str, str],
) -> list[str]:
    """Bind the rollback target to the exact currently deployed environment."""

    root = payload if isinstance(payload, dict) else {}
    rollback = root.get("rollback") if isinstance(root.get("rollback"), dict) else {}
    bindings = {
        "COMPLIANCEHUB_RELEASE_ID": rollback.get("release_id"),
        "COMPLIANCEHUB_RELEASE_COMMIT": rollback.get("commit_sha"),
        "COMPLIANCEHUB_BACKEND_IMAGE": rollback.get("backend_image"),
        "COMPLIANCEHUB_FRONTEND_IMAGE": rollback.get("frontend_image"),
        "COMPLIANCEHUB_RELEASE_EVIDENCE_SHA256": rollback.get("evidence_sha256"),
        "COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256": rollback.get("blueprint_sha256"),
    }
    errors = [
        f"current deployment {key} does not match the approved rollback target"
        for key, expected in bindings.items()
        if environment.get(key) != expected
    ]
    if rollback.get("configuration_sha256") != canonical_environment_sha256(environment):
        errors.append("current deployment does not match rollback.configuration_sha256")
    return errors


def validate_sbom_binding(
    payload: object,
    *,
    backend_sha256: str,
    frontend_sha256: str,
) -> list[str]:
    root = payload if isinstance(payload, dict) else {}
    sboms = root.get("sboms") if isinstance(root.get("sboms"), dict) else {}
    errors: list[str] = []
    if sboms.get("backend_sha256") != backend_sha256:
        errors.append("backend SBOM file does not match sboms.backend_sha256")
    if sboms.get("frontend_sha256") != frontend_sha256:
        errors.append("frontend SBOM file does not match sboms.frontend_sha256")
    return errors


def validate_release_evidence(
    payload: object,
    *,
    expected_commit: str | None = None,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    root = _mapping(payload, "release evidence", errors)
    _reject_unknown_fields(root, ROOT_FIELDS, "release evidence", errors)
    if type(root.get("schema_version")) is not int or root.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    _require_reviewed_text(root, "release_id", errors)
    _require_reviewed_text(root, "change_ticket", errors)
    built_by = _require_reviewed_text(root, "built_by", errors)
    approved_by = _require_reviewed_text(root, "approved_by", errors)
    if built_by and approved_by and built_by.casefold() == approved_by.casefold():
        errors.append("approved_by must differ from built_by (four-eyes principle)")

    commit = root.get("commit_sha")
    if not isinstance(commit, str) or not COMMIT_PATTERN.fullmatch(commit) or commit == "0" * 40:
        errors.append("commit_sha must be a full non-zero lowercase Git SHA")
    elif expected_commit and commit != expected_commit:
        errors.append("commit_sha does not match the checked-out release commit")

    created = _parse_timestamp(root.get("created_at"), "created_at", errors)
    expires = _parse_timestamp(root.get("expires_at"), "expires_at", errors)
    current = now or datetime.now(UTC)
    if created and created > current:
        errors.append("created_at cannot be in the future")
    if expires and expires <= current:
        errors.append("release evidence has expired")
    if created and expires and expires <= created:
        errors.append("expires_at must be later than created_at")
    if created and expires and expires - created > timedelta(days=30):
        errors.append("release evidence validity must not exceed 30 days")

    images = _mapping(root.get("images"), "images", errors)
    _reject_unknown_fields(images, {"backend", "frontend"}, "images", errors)
    backend_image = _require_image(images, "backend", errors, label="images.backend")
    frontend_image = _require_image(images, "frontend", errors, label="images.frontend")
    if backend_image and frontend_image and backend_image == frontend_image:
        errors.append("backend and frontend images must be distinct artifacts")

    sboms = _mapping(root.get("sboms"), "sboms", errors)
    _reject_unknown_fields(
        sboms,
        {"backend_sha256", "frontend_sha256"},
        "sboms",
        errors,
    )
    _require_digest(sboms, "backend_sha256", errors, label="sboms.backend_sha256")
    _require_digest(sboms, "frontend_sha256", errors, label="sboms.frontend_sha256")

    security = _mapping(root.get("security"), "security", errors)
    _reject_unknown_fields(
        security,
        {
            "container_scan_status",
            "maximum_allowed_severity",
            "critical_findings",
            "high_findings",
            "signature_verification_status",
            "provenance_verification_status",
        },
        "security",
        errors,
    )
    for field in (
        "container_scan_status",
        "signature_verification_status",
        "provenance_verification_status",
    ):
        if security.get(field) != "passed":
            errors.append(f"security.{field} must be passed")
    if security.get("maximum_allowed_severity") != "medium":
        errors.append("security.maximum_allowed_severity must be medium")
    for field in ("critical_findings", "high_findings"):
        if type(security.get(field)) is not int or security.get(field) != 0:
            errors.append(f"security.{field} must be zero")

    deployment = _mapping(root.get("deployment"), "deployment", errors)
    _reject_unknown_fields(
        deployment,
        {"configuration_sha256", "blueprint_sha256"},
        "deployment",
        errors,
    )
    _require_digest(
        deployment,
        "configuration_sha256",
        errors,
        label="deployment.configuration_sha256",
    )
    _require_digest(
        deployment,
        "blueprint_sha256",
        errors,
        label="deployment.blueprint_sha256",
    )

    database = _mapping(root.get("database"), "database", errors)
    _reject_unknown_fields(
        database,
        {
            "migration_plan_sha256",
            "restore_drill_id",
            "restore_evidence_sha256",
            "change_class",
            "migration_execution_status",
            "schema_verification_status",
            "rollback_compatibility_status",
        },
        "database",
        errors,
    )
    _require_digest(
        database,
        "migration_plan_sha256",
        errors,
        label="database.migration_plan_sha256",
    )
    restore_drill_id = _require_reviewed_text(database, "restore_drill_id", errors)
    if restore_drill_id and not re.fullmatch(r"DR-[0-9]{8}-[A-Z0-9]{4,16}", restore_drill_id):
        errors.append("database.restore_drill_id is invalid")
    _require_digest(
        database,
        "restore_evidence_sha256",
        errors,
        label="database.restore_evidence_sha256",
    )
    change_class = database.get("change_class")
    if change_class not in {"none", "backward_compatible_expand"}:
        errors.append("database.change_class must be none or backward_compatible_expand")
    expected_execution = "not_required" if change_class == "none" else "passed"
    if database.get("migration_execution_status") != expected_execution:
        errors.append("database.migration_execution_status must match the approved change class")
    if database.get("schema_verification_status") != "passed":
        errors.append("database.schema_verification_status must be passed")
    if database.get("rollback_compatibility_status") != "passed":
        errors.append("database.rollback_compatibility_status must be passed")

    rollback = _mapping(root.get("rollback"), "rollback", errors)
    _reject_unknown_fields(
        rollback,
        {
            "release_id",
            "commit_sha",
            "evidence_sha256",
            "configuration_sha256",
            "blueprint_sha256",
            "backend_image",
            "frontend_image",
            "tested_at",
            "evidence_reference",
        },
        "rollback",
        errors,
    )
    rollback_release_id = _require_reviewed_text(rollback, "release_id", errors)
    if rollback_release_id and rollback_release_id == root.get("release_id"):
        errors.append("rollback.release_id must differ from the release_id")
    rollback_commit = rollback.get("commit_sha")
    if (
        not isinstance(rollback_commit, str)
        or not COMMIT_PATTERN.fullmatch(rollback_commit)
        or rollback_commit == "0" * 40
    ):
        errors.append("rollback.commit_sha must be a full non-zero lowercase Git SHA")
    _require_digest(
        rollback,
        "evidence_sha256",
        errors,
        label="rollback.evidence_sha256",
    )
    _require_digest(
        rollback,
        "configuration_sha256",
        errors,
        label="rollback.configuration_sha256",
    )
    rollback_blueprint = _require_digest(
        rollback,
        "blueprint_sha256",
        errors,
        label="rollback.blueprint_sha256",
    )
    if rollback_blueprint and rollback_blueprint != deployment.get("blueprint_sha256"):
        errors.append("rollback.blueprint_sha256 must match deployment.blueprint_sha256")
    rollback_backend = _require_image(
        rollback, "backend_image", errors, label="rollback.backend_image"
    )
    rollback_frontend = _require_image(
        rollback, "frontend_image", errors, label="rollback.frontend_image"
    )
    if backend_image and rollback_backend == backend_image:
        errors.append("rollback.backend_image must differ from the release backend image")
    if frontend_image and rollback_frontend == frontend_image:
        errors.append("rollback.frontend_image must differ from the release frontend image")
    rollback_tested = _parse_timestamp(rollback.get("tested_at"), "rollback.tested_at", errors)
    if rollback_tested and rollback_tested > current:
        errors.append("rollback.tested_at cannot be in the future")
    _require_reviewed_text(rollback, "evidence_reference", errors)

    approvals = _mapping(root.get("approvals"), "approvals", errors)
    _reject_unknown_fields(approvals, set(APPROVAL_FIELDS), "approvals", errors)
    for field in APPROVAL_FIELDS:
        if approvals.get(field) != "approved":
            errors.append(f"approvals.{field} must be approved")
    _signature_entries(root, errors)
    return errors


def _current_commit() -> str:
    result = subprocess.run(  # nosec B603, B607
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _reject_duplicate_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-commit", default=None)
    parser.add_argument("--deployment-env", type=Path)
    parser.add_argument("--builder-public-key", type=Path)
    parser.add_argument("--approver-public-key", type=Path)
    parser.add_argument("--backend-sbom", type=Path)
    parser.add_argument("--frontend-sbom", type=Path)
    parser.add_argument("--restore-evidence", type=Path)
    parser.add_argument("--deployment-dir", type=Path)
    parser.add_argument("--print-signing-payload", action="store_true")
    parser.add_argument("--json", action="store_true")
    arguments = parser.parse_args()
    try:
        payload = json.loads(
            arguments.evidence.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_object,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors = [f"release evidence cannot be read: {type(exc).__name__}"]
    else:
        if arguments.print_signing_payload:
            print(canonical_signing_payload(payload).decode("utf-8"))
            return 0
        expected_commit = arguments.expected_commit
        errors = []
        if expected_commit is None:
            errors.append("--expected-commit is required for production verification")
        elif expected_commit == "HEAD":
            expected_commit = _current_commit()
        errors.extend(validate_release_evidence(payload, expected_commit=expected_commit))
        evidence_sha256 = _sha256_file(arguments.evidence, "release evidence", errors)

        if arguments.deployment_env is None:
            errors.append("--deployment-env is required for production verification")
        else:
            environment = read_environment(arguments.deployment_env, errors)
            errors.extend(
                validate_deployment_binding(
                    payload,
                    environment,
                    evidence_sha256=evidence_sha256,
                )
            )

        if arguments.deployment_dir is None:
            errors.append("--deployment-dir is required for production verification")
        else:
            try:
                blueprint_sha256 = deployment_blueprint_sha256(arguments.deployment_dir)
            except OSError:
                errors.append("deployment blueprint cannot be read")
            else:
                deployment = payload.get("deployment") if isinstance(payload, dict) else {}
                if (
                    not isinstance(deployment, dict)
                    or deployment.get("blueprint_sha256") != blueprint_sha256
                ):
                    errors.append("deployment blueprint does not match deployment.blueprint_sha256")

        if arguments.backend_sbom is None:
            errors.append("--backend-sbom is required for production verification")
            backend_sbom_sha256 = ""
        else:
            backend_sbom_sha256 = _sha256_file(arguments.backend_sbom, "backend SBOM", errors)
            errors.extend(validate_cyclonedx_sbom(arguments.backend_sbom, "backend SBOM"))
        if arguments.frontend_sbom is None:
            errors.append("--frontend-sbom is required for production verification")
            frontend_sbom_sha256 = ""
        else:
            frontend_sbom_sha256 = _sha256_file(arguments.frontend_sbom, "frontend SBOM", errors)
            errors.extend(validate_cyclonedx_sbom(arguments.frontend_sbom, "frontend SBOM"))
        if backend_sbom_sha256 and frontend_sbom_sha256:
            errors.extend(
                validate_sbom_binding(
                    payload,
                    backend_sha256=backend_sbom_sha256,
                    frontend_sha256=frontend_sbom_sha256,
                )
            )

        release_created_at = None
        if isinstance(payload, dict):
            created_value = payload.get("created_at")
            if isinstance(created_value, str):
                try:
                    parsed_created_at = datetime.fromisoformat(created_value.replace("Z", "+00:00"))
                except ValueError:
                    release_created_at = None
                else:
                    if (
                        parsed_created_at.tzinfo is not None
                        and parsed_created_at.utcoffset() == UTC.utcoffset(parsed_created_at)
                    ):
                        release_created_at = parsed_created_at
        if arguments.restore_evidence is None:
            errors.append("--restore-evidence is required for production verification")
        else:
            restore_sha256 = _sha256_file(
                arguments.restore_evidence,
                "restore drill evidence",
                errors,
            )
            errors.extend(
                validate_restore_drill_evidence(
                    arguments.restore_evidence,
                    release_created_at=release_created_at,
                )
            )
            database = payload.get("database") if isinstance(payload, dict) else {}
            if (
                not isinstance(database, dict)
                or database.get("restore_evidence_sha256") != restore_sha256
            ):
                errors.append(
                    "restore drill evidence file does not match database.restore_evidence_sha256"
                )
            try:
                restore_payload = json.loads(
                    arguments.restore_evidence.read_text(encoding="utf-8"),
                    object_pairs_hook=_reject_duplicate_json_object,
                )
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                restore_payload = {}
            if (
                not isinstance(database, dict)
                or not isinstance(restore_payload, dict)
                or database.get("restore_drill_id") != restore_payload.get("drill_id")
            ):
                errors.append("restore drill evidence does not match database.restore_drill_id")

        if arguments.builder_public_key is None:
            errors.append("--builder-public-key is required for production verification")
            builder_key = None
        else:
            builder_key = _load_ed25519_public_key(
                arguments.builder_public_key, "trusted builder", errors
            )
        if arguments.approver_public_key is None:
            errors.append("--approver-public-key is required for production verification")
            approver_key = None
        else:
            approver_key = _load_ed25519_public_key(
                arguments.approver_public_key, "trusted approver", errors
            )
        if builder_key is not None and approver_key is not None:
            errors.extend(
                verify_release_signatures(
                    payload,
                    builder_public_key=builder_key,
                    approver_public_key=approver_key,
                )
            )

    if arguments.json:
        print(json.dumps({"passed": not errors, "errors": errors}, ensure_ascii=False))
    elif errors:
        print("Release evidence verification failed:")
        for error in errors:
            print(f"- {error}")
    else:
        print("Release evidence verification passed")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
