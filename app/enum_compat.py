from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11 fallback
    from enum import Enum

    class StrEnum(str, Enum):
        """Backport von enum.StrEnum für Python 3.10-Testumgebungen."""


__all__ = ["StrEnum"]
