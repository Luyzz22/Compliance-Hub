"""Fail-closed reader for secrets mounted by OpenBao or the container runtime."""

from __future__ import annotations

import os
import stat
from pathlib import Path

_APPROVED_MODES = {0o400, 0o600}
_MAX_SECRET_BYTES = 64 * 1024


def production_runtime() -> bool:
    return os.getenv("COMPLIANCEHUB_ENV", "dev").strip().lower() in {
        "prod",
        "production",
    }


def _read_secret_file(file_variable: str, raw_path: str) -> str:
    path = Path(raw_path)
    if not path.is_absolute():
        raise RuntimeError(f"{file_variable} must be an absolute path")

    try:
        link_metadata = path.lstat()
        mode = stat.S_IMODE(link_metadata.st_mode)
        if not stat.S_ISREG(link_metadata.st_mode) or path.is_symlink():
            raise RuntimeError(f"{file_variable} must reference a regular file, not a symlink")
        if mode not in _APPROVED_MODES:
            raise RuntimeError(f"{file_variable} must use mode 0400 or 0600")
        if link_metadata.st_size > _MAX_SECRET_BYTES:
            raise RuntimeError(f"{file_variable} exceeds the maximum secret size")

        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened_metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened_metadata.st_mode)
                or opened_metadata.st_dev != link_metadata.st_dev
                or opened_metadata.st_ino != link_metadata.st_ino
            ):
                raise RuntimeError(f"{file_variable} changed during validation")
            with os.fdopen(os.dup(descriptor), encoding="utf-8") as handle:
                value = handle.read(_MAX_SECRET_BYTES + 1).strip()
        finally:
            os.close(descriptor)
    except RuntimeError:
        raise
    except OSError as exc:
        raise RuntimeError(f"{file_variable} cannot be read ({type(exc).__name__})") from exc

    if len(value.encode("utf-8")) > _MAX_SECRET_BYTES:
        raise RuntimeError(f"{file_variable} exceeds the maximum secret size")
    return value


def read_secret(
    environment_variable: str,
    file_environment_variable: str,
    *,
    required: bool = False,
    minimum_characters: int = 1,
) -> str:
    """Read a dev env value or a production secret file without exposing its content."""
    direct = os.getenv(environment_variable, "").strip()
    file_path = os.getenv(file_environment_variable, "").strip()
    if direct and file_path:
        raise RuntimeError(f"Set only {environment_variable} or {file_environment_variable}")
    if production_runtime() and direct:
        raise RuntimeError(
            f"{environment_variable} is forbidden in production; mount "
            f"{file_environment_variable} from OpenBao"
        )

    value = _read_secret_file(file_environment_variable, file_path) if file_path else direct
    if not value:
        if required:
            raise RuntimeError(f"{file_environment_variable} is required")
        return ""
    if len(value) < minimum_characters:
        raise RuntimeError(
            f"{file_environment_variable} must contain at least {minimum_characters} characters"
        )
    return value
