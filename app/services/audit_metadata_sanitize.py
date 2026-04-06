"""Redact sensitive keys and bound payload size for governance audit metadata."""

from __future__ import annotations

import json
from typing import Any

_SENSITIVE_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "api-key",
    "refresh",
    "private_key",
)

_MAX_STRING = 500
_MAX_DEPTH = 6


def _key_is_sensitive(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in _SENSITIVE_SUBSTRINGS)


def sanitize_audit_metadata(value: Any, *, _depth: int = 0) -> Any:
    """Return a JSON-serialisable structure safe to persist in audit metadata."""
    if _depth > _MAX_DEPTH:
        return "[TRUNCATED_DEPTH]"
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if _key_is_sensitive(str(k)):
                out[str(k)] = "[REDACTED]"
            else:
                out[str(k)] = sanitize_audit_metadata(v, _depth=_depth + 1)
        return out
    if isinstance(value, list):
        return [sanitize_audit_metadata(v, _depth=_depth + 1) for v in value[:50]]
    if isinstance(value, str):
        return value if len(value) <= _MAX_STRING else value[:_MAX_STRING] + "…"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:_MAX_STRING]


def metadata_json_safe(metadata: dict[str, Any] | None) -> str | None:
    if not metadata:
        return None
    return json.dumps(sanitize_audit_metadata(metadata), sort_keys=True, default=str)
