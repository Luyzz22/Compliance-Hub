from __future__ import annotations

try:
    from enum import StrEnum  # type: ignore[assignment]
except ImportError:  # pragma: no cover - Python < 3.11 fallback
    from enum import Enum

    class StrEnum(str, Enum):  # noqa: UP042
        """Backport von enum.StrEnum für Python 3.10-Testumgebungen."""
        pass


__all__ = ["StrEnum"]

