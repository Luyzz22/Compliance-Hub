"""Reine Coverage-Logik (testbar ohne DB)."""

from __future__ import annotations

from typing import Literal

ReqStatus = Literal["gap", "partial", "full", "planned_only"]


def best_coverage_levels_for_requirement(link_levels: list[str]) -> ReqStatus:
    """
    Aggregiert mehrere Links zu einem Requirement zu einem UI-Status.

    „Covered“ für Kennzahlen: mindestens full oder partial.
    """
    if not link_levels:
        return "gap"
    norm = {str(x).strip().lower() for x in link_levels}
    if "full" in norm:
        return "full"
    if "partial" in norm:
        return "partial"
    if "planned" in norm:
        return "planned_only"
    return "gap"


def is_requirement_covered(link_levels: list[str]) -> bool:
    """True, wenn mindestens ein Link full oder partial ist."""
    return best_coverage_levels_for_requirement(link_levels) in ("full", "partial")


def framework_coverage_percent(*, total: int, covered: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * min(covered, total) / total, 1)
