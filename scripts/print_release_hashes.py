#!/usr/bin/env python3
"""Print deterministic hashes needed before signing release evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

if __package__:
    from scripts.verify_release_evidence import (
        canonical_environment_sha256,
        deployment_blueprint_sha256,
        read_environment,
    )
else:  # pragma: no cover - deployment-host entrypoint
    from verify_release_evidence import (  # type: ignore[no-redef]
        canonical_environment_sha256,
        deployment_blueprint_sha256,
        read_environment,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--deployment-env", type=Path, required=True)
    parser.add_argument("--deployment-dir", type=Path, required=True)
    arguments = parser.parse_args()
    errors: list[str] = []
    environment = read_environment(arguments.deployment_env, errors)
    try:
        blueprint_sha256 = deployment_blueprint_sha256(arguments.deployment_dir)
    except OSError:
        errors.append("deployment blueprint cannot be read")
        blueprint_sha256 = ""
    if (
        blueprint_sha256
        and environment.get("COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256") != blueprint_sha256
    ):
        errors.append(
            "COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256 must first be set to the reported "
            "blueprint_sha256"
        )
    if errors:
        print(
            json.dumps(
                {
                    "passed": False,
                    "errors": errors,
                    "blueprint_sha256": blueprint_sha256,
                },
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "passed": True,
                "configuration_sha256": canonical_environment_sha256(environment),
                "blueprint_sha256": blueprint_sha256,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
