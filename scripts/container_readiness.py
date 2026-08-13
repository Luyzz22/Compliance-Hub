#!/usr/bin/env python3
"""Container-local readiness probe without exposing its credential in argv."""

from __future__ import annotations

import http.client
import json
import os
import stat
from pathlib import Path

MAX_SECRET_BYTES = 64 * 1024


def _read_health_key() -> str:
    raw_path = os.getenv("INTERNAL_HEALTH_API_KEY_FILE", "").strip()
    if not raw_path:
        raise RuntimeError("INTERNAL_HEALTH_API_KEY_FILE is required")
    path = Path(raw_path)
    if not path.is_absolute():
        raise RuntimeError("INTERNAL_HEALTH_API_KEY_FILE must be absolute")
    metadata = path.lstat()
    mode = stat.S_IMODE(metadata.st_mode)
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise RuntimeError("health credential must be a regular non-symlink file")
    if mode not in {0o400, 0o600}:
        raise RuntimeError("health credential must use mode 0400 or 0600")
    if metadata.st_size > MAX_SECRET_BYTES:
        raise RuntimeError("health credential is too large")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if opened.st_dev != metadata.st_dev or opened.st_ino != metadata.st_ino:
            raise RuntimeError("health credential changed during validation")
        with os.fdopen(os.dup(descriptor), encoding="utf-8") as handle:
            value = handle.read(MAX_SECRET_BYTES + 1).strip()
    finally:
        os.close(descriptor)
    if len(value.encode("utf-8")) < 32:
        raise RuntimeError("health credential must contain at least 32 bytes")
    return value


def main() -> int:
    try:
        public_host = os.getenv("COMPLIANCEHUB_PUBLIC_HOST", "").strip().lower()
        if not public_host or any(character in public_host for character in "/:@[]"):
            raise RuntimeError("COMPLIANCEHUB_PUBLIC_HOST is required for the health Host header")
        connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=3)
        connection.request(
            "GET",
            "/api/internal/readiness",
            headers={
                "Host": public_host,
                "X-HEALTH-KEY": _read_health_key(),
            },
        )
        response = connection.getresponse()
        try:
            payload = json.loads(response.read(MAX_SECRET_BYTES + 1))
            status = response.status
        finally:
            connection.close()
        if (
            status != 200
            or payload.get("app") != "up"
            or payload.get("db") != "up"
            or payload.get("policy_engine") != "up"
        ):
            return 1
        return 0
    except (OSError, RuntimeError, ValueError, http.client.HTTPException):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
