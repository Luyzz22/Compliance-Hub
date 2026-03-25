"""Whitelist für runtime event `extra` (DSGVO-Minimierung, kein Freitext)."""

from __future__ import annotations

import re
from typing import Any

_EXTRA_ALLOWED_KEYS = frozenset(
    {"region", "correlation_id", "sap_resource_name", "surface"},
)
_STR_PATTERN = re.compile(r"^[a-zA-Z0-9_.:/\-]{1,128}$")


def sanitize_runtime_event_extra(raw: dict[str, Any] | None) -> dict[str, str | int | bool]:
    if not raw:
        return {}
    out: dict[str, str | int | bool] = {}
    for k, v in raw.items():
        if not isinstance(k, str) or not k.strip():
            continue
        kn = k.strip()
        if kn not in _EXTRA_ALLOWED_KEYS:
            continue
        if isinstance(v, bool):
            out[kn] = v
        elif isinstance(v, int) and -1_000_000_000 <= v <= 1_000_000_000:
            out[kn] = v
        elif isinstance(v, str) and _STR_PATTERN.fullmatch(v):
            out[kn] = v
    return out
