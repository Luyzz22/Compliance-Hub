"""Production release evidence must bind approvals to immutable artifacts."""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from datetime import UTC, datetime

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts.verify_release_evidence import (
    canonical_environment_sha256,
    canonical_signing_payload,
    deployment_blueprint_sha256,
    read_environment,
    validate_cyclonedx_sbom,
    validate_deployment_binding,
    validate_release_evidence,
    validate_restore_drill_evidence,
    validate_rollback_binding,
    validate_sbom_binding,
    verify_release_signatures,
)

NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64


def _valid_evidence() -> dict:
    return {
        "schema_version": 1,
        "release_id": "REL-2026-0812-01",
        "commit_sha": "a" * 40,
        "created_at": "2026-08-12T10:00:00Z",
        "expires_at": "2026-08-19T10:00:00Z",
        "built_by": "ci-builder-prod",
        "approved_by": "security-reviewer-01",
        "change_ticket": "CHG-4815",
        "images": {
            "backend": f"registry.internal/compliancehub/backend@sha256:{DIGEST_A}",
            "frontend": f"registry.internal/compliancehub/frontend@sha256:{DIGEST_B}",
        },
        "sboms": {
            "backend_sha256": DIGEST_C,
            "frontend_sha256": DIGEST_D,
        },
        "security": {
            "container_scan_status": "passed",
            "maximum_allowed_severity": "medium",
            "critical_findings": 0,
            "high_findings": 0,
            "signature_verification_status": "passed",
            "provenance_verification_status": "passed",
        },
        "deployment": {
            "configuration_sha256": DIGEST_A,
            "blueprint_sha256": DIGEST_B,
        },
        "database": {
            "migration_plan_sha256": DIGEST_A,
            "restore_drill_id": "DR-20260811-CHANGE4815",
            "restore_evidence_sha256": DIGEST_B,
            "change_class": "none",
            "migration_execution_status": "not_required",
            "schema_verification_status": "passed",
            "rollback_compatibility_status": "passed",
        },
        "rollback": {
            "release_id": "REL-2026-0801-04",
            "commit_sha": "b" * 40,
            "evidence_sha256": DIGEST_B,
            "configuration_sha256": DIGEST_C,
            "blueprint_sha256": DIGEST_B,
            "backend_image": f"registry.internal/compliancehub/backend@sha256:{DIGEST_C}",
            "frontend_image": f"registry.internal/compliancehub/frontend@sha256:{DIGEST_D}",
            "tested_at": "2026-08-11T09:00:00Z",
            "evidence_reference": "evidence://rollback/2026-08-11/approved",
        },
        "approvals": {
            "security": "approved",
            "privacy": "approved",
            "operations": "approved",
            "product_owner": "approved",
        },
        "signatures": [
            {
                "role": "builder",
                "subject": "ci-builder-prod",
                "algorithm": "Ed25519",
                "key_id": "1" * 64,
                "signature": base64.b64encode(b"a" * 64).decode("ascii"),
            },
            {
                "role": "approver",
                "subject": "security-reviewer-01",
                "algorithm": "Ed25519",
                "key_id": "2" * 64,
                "signature": base64.b64encode(b"b" * 64).decode("ascii"),
            },
        ],
    }


def _valid_restore_evidence() -> dict:
    return {
        "schema_version": 1,
        "drill_id": "DR-20260811-CHANGE4815",
        "started_at": "2026-08-11T08:00:00Z",
        "completed_at": "2026-08-11T09:00:00Z",
        "tools": {
            "psql": "17.9",
            "pg_restore": "17.9",
            "createdb": "17.9",
            "dropdb": "17.9",
            "rclone": "v1.72.1",
        },
        "postgres": {
            "status": "passed",
            "public_table_count": 64,
            "required_tables": ["tenants", "ai_systems", "audit_logs", "evidence_files"],
            "restore_seconds": 120.5,
            "cleanup_status": "passed",
            "backup_sha256": DIGEST_A,
            "backup_created_at": "2026-08-11T07:45:00Z",
            "restore_host_sha256": DIGEST_B,
        },
        "object_storage": {
            "status": "passed",
            "object_count": 18,
            "total_bytes": 4096,
            "verified_object_count": 18,
            "restore_seconds": 90.25,
            "cleanup_status": "passed",
            "backup_reference_sha256": DIGEST_C,
            "backup_created_at": "2026-08-11T07:45:00Z",
            "endpoint_host_sha256": DIGEST_D,
        },
        "recovery": {
            "status": "passed",
            "rpo_minutes": 15.0,
            "rpo_target_minutes": 1440,
            "rto_seconds": 3600.0,
            "rto_target_seconds": 14400,
        },
    }


def _key_id(private_key: Ed25519PrivateKey) -> str:
    raw_public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    return hashlib.sha256(raw_public_key).hexdigest()


def _sign_evidence(
    evidence: dict,
    builder_key: Ed25519PrivateKey,
    approver_key: Ed25519PrivateKey,
) -> None:
    evidence["signatures"] = [
        {
            "role": "builder",
            "subject": evidence["built_by"],
            "algorithm": "Ed25519",
            "key_id": _key_id(builder_key),
            "signature": "",
        },
        {
            "role": "approver",
            "subject": evidence["approved_by"],
            "algorithm": "Ed25519",
            "key_id": _key_id(approver_key),
            "signature": "",
        },
    ]
    message = canonical_signing_payload(evidence)
    evidence["signatures"][0]["signature"] = base64.b64encode(builder_key.sign(message)).decode(
        "ascii"
    )
    evidence["signatures"][1]["signature"] = base64.b64encode(approver_key.sign(message)).decode(
        "ascii"
    )


def test_valid_release_evidence_passes() -> None:
    evidence = _valid_evidence()
    assert validate_release_evidence(evidence, expected_commit="a" * 40, now=NOW) == []


def test_example_evidence_is_fail_closed() -> None:
    evidence = _valid_evidence()
    evidence["images"]["backend"] = (
        "registry.example.invalid/compliancehub/backend@sha256:" + "0" * 64
    )
    evidence["security"]["container_scan_status"] = "pending"
    evidence["approvals"]["privacy"] = "pending"

    errors = validate_release_evidence(evidence, now=NOW)

    assert any("images.backend" in error for error in errors)
    assert "security.container_scan_status must be passed" in errors
    assert "approvals.privacy must be approved" in errors


def test_four_eyes_and_commit_binding_are_required() -> None:
    evidence = _valid_evidence()
    evidence["approved_by"] = evidence["built_by"]

    errors = validate_release_evidence(evidence, expected_commit="b" * 40, now=NOW)

    assert "approved_by must differ from built_by (four-eyes principle)" in errors
    assert "commit_sha does not match the checked-out release commit" in errors


def test_expired_evidence_and_release_as_rollback_are_rejected() -> None:
    evidence = deepcopy(_valid_evidence())
    evidence["expires_at"] = "2026-08-12T11:00:00Z"
    evidence["rollback"]["backend_image"] = evidence["images"]["backend"]

    errors = validate_release_evidence(evidence, now=NOW)

    assert "release evidence has expired" in errors
    assert "rollback.backend_image must differ from the release backend image" in errors


def test_database_change_must_preserve_runtime_rollback_compatibility() -> None:
    evidence = _valid_evidence()
    evidence["database"]["change_class"] = "breaking_contract"
    evidence["database"]["migration_execution_status"] = "passed"
    evidence["database"]["rollback_compatibility_status"] = "pending"

    errors = validate_release_evidence(evidence, now=NOW)

    assert "database.change_class must be none or backward_compatible_expand" in errors
    assert "database.rollback_compatibility_status must be passed" in errors


def test_unknown_fields_and_boolean_schema_versions_are_rejected() -> None:
    evidence = _valid_evidence()
    evidence["schema_version"] = True
    evidence["security"]["critical_findings"] = False
    evidence["security"]["unreviewed_override"] = True

    errors = validate_release_evidence(evidence, now=NOW)

    assert "schema_version must be 1" in errors
    assert "security.critical_findings must be zero" in errors
    assert "security contains unsupported field unreviewed_override" in errors


def test_independent_ed25519_signatures_cover_the_complete_release() -> None:
    evidence = _valid_evidence()
    builder_key = Ed25519PrivateKey.generate()
    approver_key = Ed25519PrivateKey.generate()
    _sign_evidence(evidence, builder_key, approver_key)

    assert (
        verify_release_signatures(
            evidence,
            builder_public_key=builder_key.public_key(),
            approver_public_key=approver_key.public_key(),
        )
        == []
    )

    evidence["approvals"]["privacy"] = "pending"
    errors = verify_release_signatures(
        evidence,
        builder_public_key=builder_key.public_key(),
        approver_public_key=approver_key.public_key(),
    )
    assert "builder Ed25519 signature is invalid" in errors
    assert "approver Ed25519 signature is invalid" in errors


def test_signature_key_ids_and_independent_trust_roots_are_enforced() -> None:
    evidence = _valid_evidence()
    builder_key = Ed25519PrivateKey.generate()
    approver_key = Ed25519PrivateKey.generate()
    _sign_evidence(evidence, builder_key, approver_key)

    wrong_key = Ed25519PrivateKey.generate()
    errors = verify_release_signatures(
        evidence,
        builder_public_key=wrong_key.public_key(),
        approver_public_key=approver_key.public_key(),
    )
    assert "builder key_id does not match the trusted public key" in errors

    errors = verify_release_signatures(
        evidence,
        builder_public_key=builder_key.public_key(),
        approver_public_key=builder_key.public_key(),
    )
    assert errors == ["trusted builder and approver public keys must differ"]


def test_deployment_environment_is_bound_to_release_id_images_and_evidence_hash() -> None:
    evidence = _valid_evidence()
    environment = {
        "COMPLIANCEHUB_RELEASE_ID": evidence["release_id"],
        "COMPLIANCEHUB_RELEASE_COMMIT": evidence["commit_sha"],
        "COMPLIANCEHUB_BACKEND_IMAGE": evidence["images"]["backend"],
        "COMPLIANCEHUB_FRONTEND_IMAGE": evidence["images"]["frontend"],
        "COMPLIANCEHUB_RELEASE_EVIDENCE_SHA256": DIGEST_A,
        "COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256": evidence["deployment"]["blueprint_sha256"],
    }
    evidence["deployment"]["configuration_sha256"] = canonical_environment_sha256(environment)

    assert validate_deployment_binding(evidence, environment, evidence_sha256=DIGEST_A) == []
    environment["COMPLIANCEHUB_FRONTEND_IMAGE"] = evidence["rollback"]["frontend_image"]
    assert validate_deployment_binding(evidence, environment, evidence_sha256=DIGEST_A) == [
        "deployment environment COMPLIANCEHUB_FRONTEND_IMAGE does not match release evidence",
        "deployment environment does not match deployment.configuration_sha256",
    ]


def test_current_environment_must_match_the_signed_rollback_target() -> None:
    evidence = _valid_evidence()
    rollback = evidence["rollback"]
    environment = {
        "COMPLIANCEHUB_RELEASE_ID": rollback["release_id"],
        "COMPLIANCEHUB_RELEASE_COMMIT": rollback["commit_sha"],
        "COMPLIANCEHUB_BACKEND_IMAGE": rollback["backend_image"],
        "COMPLIANCEHUB_FRONTEND_IMAGE": rollback["frontend_image"],
        "COMPLIANCEHUB_RELEASE_EVIDENCE_SHA256": rollback["evidence_sha256"],
        "COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256": rollback["blueprint_sha256"],
    }
    rollback["configuration_sha256"] = canonical_environment_sha256(environment)

    assert validate_rollback_binding(evidence, environment) == []
    environment["COMPLIANCEHUB_RELEASE_ID"] = "unexpected"
    assert validate_rollback_binding(evidence, environment) == [
        "current deployment COMPLIANCEHUB_RELEASE_ID does not match the approved rollback target",
        "current deployment does not match rollback.configuration_sha256",
    ]


def test_sbom_files_are_bound_to_recorded_digests() -> None:
    evidence = _valid_evidence()
    assert (
        validate_sbom_binding(
            evidence,
            backend_sha256=DIGEST_C,
            frontend_sha256=DIGEST_D,
        )
        == []
    )
    assert validate_sbom_binding(
        evidence,
        backend_sha256=DIGEST_A,
        frontend_sha256=DIGEST_D,
    ) == ["backend SBOM file does not match sboms.backend_sha256"]


def test_restore_drill_evidence_requires_measured_restore_and_cleanup(tmp_path) -> None:
    path = tmp_path / "restore-drill.json"
    path.write_text(json.dumps(_valid_restore_evidence()), encoding="utf-8")
    assert validate_restore_drill_evidence(path, release_created_at=NOW) == []

    payload = _valid_restore_evidence()
    payload["object_storage"]["verified_object_count"] = 17
    payload["postgres"]["cleanup_status"] = "failed"
    payload["recovery"]["rto_seconds"] = 20_000
    path.write_text(json.dumps(payload), encoding="utf-8")
    errors = validate_restore_drill_evidence(path, release_created_at=NOW)
    assert "restore drill postgres.cleanup_status must be passed" in errors
    assert "restore drill object_storage.verified_object_count must match object_count" in errors
    assert "restore drill recovery.rto_seconds exceeds rto_target_seconds" in errors
    assert "restore drill recovery.rto_seconds does not match drill timestamps" in errors


def test_restore_drill_validation_handles_invalid_release_timestamp_without_crashing(
    tmp_path,
) -> None:
    path = tmp_path / "restore-drill.json"
    path.write_text(json.dumps(_valid_restore_evidence()), encoding="utf-8")
    assert validate_restore_drill_evidence(path, release_created_at=None) == []


def test_cyclonedx_sbom_requires_a_supported_non_empty_document(tmp_path) -> None:
    valid = tmp_path / "valid.cdx.json"
    valid.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "version": 1,
                "components": [{"type": "library", "name": "fastapi", "version": "0.141.1"}],
            }
        ),
        encoding="utf-8",
    )
    assert validate_cyclonedx_sbom(valid, "backend SBOM") == []

    invalid = tmp_path / "invalid.cdx.json"
    invalid.write_text(
        '{"bomFormat":"CycloneDX","version":false,"components":[]}', encoding="utf-8"
    )
    errors = validate_cyclonedx_sbom(invalid, "backend SBOM")
    assert "backend SBOM.specVersion must be a supported CycloneDX version" in errors
    assert "backend SBOM.version must be a positive integer" in errors
    assert "backend SBOM.components must be a non-empty array" in errors


def test_production_cli_verifies_keys_sboms_environment_and_evidence_hash(tmp_path) -> None:
    evidence = _valid_evidence()
    backend_sbom = tmp_path / "backend.cdx.json"
    frontend_sbom = tmp_path / "frontend.cdx.json"
    backend_sbom.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "version": 1,
                "components": [{"type": "library", "name": "fastapi", "version": "0.141.1"}],
            }
        ),
        encoding="utf-8",
    )
    frontend_sbom.write_text(
        json.dumps(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.6",
                "version": 1,
                "components": [{"type": "library", "name": "next", "version": "16.3.0"}],
            }
        ),
        encoding="utf-8",
    )
    evidence["sboms"] = {
        "backend_sha256": hashlib.sha256(backend_sbom.read_bytes()).hexdigest(),
        "frontend_sha256": hashlib.sha256(frontend_sbom.read_bytes()).hexdigest(),
    }
    restore_evidence = tmp_path / "restore-drill.json"
    restore_evidence.write_text(json.dumps(_valid_restore_evidence()), encoding="utf-8")
    evidence["database"]["restore_evidence_sha256"] = hashlib.sha256(
        restore_evidence.read_bytes()
    ).hexdigest()
    deployment_dir = tmp_path / "deploy" / "hetzner"
    deployment_dir.mkdir(parents=True)
    (deployment_dir / "compose.yml").write_text("services: {}\n", encoding="utf-8")
    (deployment_dir / "Caddyfile").write_text("{ admin off }\n", encoding="utf-8")
    policy_directory = tmp_path / "infra" / "opa" / "policies" / "compliancehub" / "regos"
    policy_directory.mkdir(parents=True)
    (policy_directory / "action_policy.rego").write_text("package test\n", encoding="utf-8")
    blueprint_hash = deployment_blueprint_sha256(deployment_dir)
    evidence["deployment"]["blueprint_sha256"] = blueprint_hash
    evidence["rollback"]["blueprint_sha256"] = blueprint_hash

    environment_values = {
        "COMPLIANCEHUB_RELEASE_ID": evidence["release_id"],
        "COMPLIANCEHUB_RELEASE_COMMIT": evidence["commit_sha"],
        "COMPLIANCEHUB_BACKEND_IMAGE": evidence["images"]["backend"],
        "COMPLIANCEHUB_FRONTEND_IMAGE": evidence["images"]["frontend"],
        "COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256": blueprint_hash,
    }
    evidence["deployment"]["configuration_sha256"] = canonical_environment_sha256(
        environment_values
    )

    builder_key = Ed25519PrivateKey.generate()
    approver_key = Ed25519PrivateKey.generate()
    _sign_evidence(evidence, builder_key, approver_key)
    evidence_path = tmp_path / "release-evidence.json"
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

    builder_public_key = tmp_path / "builder.pem"
    approver_public_key = tmp_path / "approver.pem"
    for path, key in (
        (builder_public_key, builder_key),
        (approver_public_key, approver_key),
    ):
        path.write_bytes(
            key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

    environment = tmp_path / ".env.production"
    environment_values["COMPLIANCEHUB_RELEASE_EVIDENCE_SHA256"] = hashlib.sha256(
        evidence_path.read_bytes()
    ).hexdigest()
    environment.write_text(
        "\n".join(f"{key}={value}" for key, value in environment_values.items()),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_release_evidence.py",
            str(evidence_path),
            "--expected-commit",
            evidence["commit_sha"],
            "--deployment-env",
            str(environment),
            "--builder-public-key",
            str(builder_public_key),
            "--approver-public-key",
            str(approver_public_key),
            "--backend-sbom",
            str(backend_sbom),
            "--frontend-sbom",
            str(frontend_sbom),
            "--restore-evidence",
            str(restore_evidence),
            "--deployment-dir",
            str(deployment_dir),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout) == {"passed": True, "errors": []}


def test_production_cli_requires_an_explicit_commit_binding(tmp_path) -> None:
    evidence_path = tmp_path / "release-evidence.json"
    evidence_path.write_text(json.dumps(_valid_evidence()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/verify_release_evidence.py",
            str(evidence_path),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert (
        "--expected-commit is required for production verification"
        in json.loads(result.stdout)["errors"]
    )


def test_deployment_environment_rejects_shell_and_dotenv_interpolation(tmp_path) -> None:
    environment = tmp_path / ".env.production"
    environment.write_text(
        "SAFE=value\nEXPANDED=${UNTRUSTED}\nQUOTED='ambiguous'\n",
        encoding="utf-8",
    )
    errors: list[str] = []

    parsed = read_environment(environment, errors)

    assert parsed == {"SAFE": "value"}
    assert len(errors) == 2
    assert all("approved literal dotenv subset" in error for error in errors)
