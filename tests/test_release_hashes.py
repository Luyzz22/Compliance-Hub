"""Release hash preparation must not sign a stale blueprint reference."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.verify_release_evidence import deployment_blueprint_sha256


def _deployment(tmp_path: Path) -> Path:
    deployment = tmp_path / "deploy" / "hetzner"
    deployment.mkdir(parents=True)
    (deployment / "compose.yml").write_text("services: {}\n", encoding="utf-8")
    (deployment / "Caddyfile").write_text("{ admin off }\n", encoding="utf-8")
    policy = tmp_path / "infra" / "opa" / "policies" / "compliancehub" / "regos"
    policy.mkdir(parents=True)
    (policy / "action_policy.rego").write_text("package test\n", encoding="utf-8")
    return deployment


def test_hash_helper_requires_blueprint_value_before_configuration_hash(
    tmp_path: Path,
) -> None:
    deployment = _deployment(tmp_path)
    environment = tmp_path / ".env.candidate"
    environment.write_text(
        "COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256=" + "0" * 64 + "\n",
        encoding="utf-8",
    )

    first = subprocess.run(
        [
            sys.executable,
            "scripts/print_release_hashes.py",
            "--deployment-env",
            str(environment),
            "--deployment-dir",
            str(deployment),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    first_payload = json.loads(first.stdout)
    assert first.returncode == 1
    blueprint_hash = deployment_blueprint_sha256(deployment)
    assert first_payload["blueprint_sha256"] == blueprint_hash

    environment.write_text(
        f"COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256={blueprint_hash}\n",
        encoding="utf-8",
    )
    second = subprocess.run(
        [
            sys.executable,
            "scripts/print_release_hashes.py",
            "--deployment-env",
            str(environment),
            "--deployment-dir",
            str(deployment),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    second_payload = json.loads(second.stdout)
    assert second.returncode == 0
    assert second_payload["passed"] is True
    assert len(second_payload["configuration_sha256"]) == 64
