#!/usr/bin/env python3
"""Prepare and validate immutable host files mounted into synthetic-demo containers."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path
from typing import TypeAlias

BASE = Path(__file__).resolve().parent

HostFileContract: TypeAlias = tuple[tuple[Path, int, int, int], ...]

# Docker Compose implements local configs as bind mounts and cannot apply uid/gid/mode.
# The host therefore owns this enforcement boundary, and the preflight revalidates it.
CONFIG_CONTRACT: HostFileContract = (
    (BASE / "Caddyfile.synthetic-demo", 65532, 65532, 0o400),
    (BASE / "postgres-init-synthetic-demo.sh", 70, 70, 0o400),
    (BASE / "apply-synthetic-demo-runtime-policy.sh", 70, 70, 0o400),
    (BASE / "../../db/postgres/migrations/20260715_advisor_runtime_state_rls.sql", 70, 70, 0o400),
    (
        BASE / "../../infra/opa/policies/compliancehub/regos/action_policy.rego",
        10001,
        10001,
        0o400,
    ),
)


class HostFileContractError(RuntimeError):
    """Raised when a protected host file violates the runtime contract."""


def _open_regular_file(path: Path) -> tuple[int, os.stat_result]:
    metadata = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise HostFileContractError(f"{path.name} must be a regular non-symlink file")
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    opened = os.fstat(descriptor)
    if (
        opened.st_dev != metadata.st_dev
        or opened.st_ino != metadata.st_ino
        or not stat.S_ISREG(opened.st_mode)
    ):
        os.close(descriptor)
        raise HostFileContractError(f"{path.name} changed during secure open")
    return descriptor, opened


def validate_host_files(contract: HostFileContract = CONFIG_CONTRACT) -> None:
    """Fail closed unless every bind-mounted config has its exact container identity."""

    for path, expected_uid, expected_gid, expected_mode in contract:
        descriptor, opened = _open_regular_file(path)
        try:
            final = os.fstat(descriptor)
            if (
                final.st_dev != opened.st_dev
                or final.st_ino != opened.st_ino
                or final.st_uid != expected_uid
                or final.st_gid != expected_gid
                or stat.S_IMODE(final.st_mode) != expected_mode
            ):
                raise HostFileContractError(
                    f"{path.name} must use numeric owner {expected_uid}:{expected_gid} "
                    f"and mode {expected_mode:04o}"
                )
        finally:
            os.close(descriptor)


def prepare_host_files(contract: HostFileContract = CONFIG_CONTRACT) -> None:
    """Apply the exact host-side ownership and mode contract without following symlinks."""

    if os.geteuid() != 0:
        raise HostFileContractError("host-file preparation must run as root")
    for path, expected_uid, expected_gid, expected_mode in contract:
        descriptor, opened = _open_regular_file(path)
        try:
            os.fchown(descriptor, expected_uid, expected_gid)
            os.fchmod(descriptor, expected_mode)
            final = os.fstat(descriptor)
            if final.st_dev != opened.st_dev or final.st_ino != opened.st_ino:
                raise HostFileContractError(f"{path.name} changed during preparation")
        finally:
            os.close(descriptor)
    validate_host_files(contract)


def main() -> int:
    prepare_host_files()
    print("synthetic_demo_host_files=prepared secrets_disclosed=false production_ready=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, HostFileContractError) as error:
        print(f"synthetic_demo_host_files=failed reason={error}", file=sys.stderr)
        raise SystemExit(1) from None
