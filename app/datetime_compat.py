from __future__ import annotations

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python < 3.11 fallback
    from datetime import timezone as _timezone

    UTC = _timezone.utc  # noqa: UP017


__all__ = ["UTC"]

