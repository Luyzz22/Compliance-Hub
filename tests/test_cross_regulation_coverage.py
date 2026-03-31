"""Unit-Tests: Coverage-Hilfsfunktionen Cross-Regulation."""

from __future__ import annotations

from app.services.cross_regulation_coverage import (
    best_coverage_levels_for_requirement,
    framework_coverage_percent,
    is_requirement_covered,
)


def test_best_coverage_empty_is_gap() -> None:
    assert best_coverage_levels_for_requirement([]) == "gap"


def test_best_coverage_full_wins() -> None:
    assert best_coverage_levels_for_requirement(["partial", "full", "planned"]) == "full"


def test_best_coverage_partial() -> None:
    assert best_coverage_levels_for_requirement(["planned", "partial"]) == "partial"


def test_best_coverage_planned_only() -> None:
    assert best_coverage_levels_for_requirement(["planned"]) == "planned_only"


def test_is_requirement_covered() -> None:
    assert is_requirement_covered(["full"]) is True
    assert is_requirement_covered(["partial"]) is True
    assert is_requirement_covered(["planned"]) is False
    assert is_requirement_covered([]) is False


def test_framework_coverage_percent() -> None:
    assert framework_coverage_percent(total=0, covered=0) == 0.0
    assert framework_coverage_percent(total=10, covered=3) == 30.0
    assert framework_coverage_percent(total=3, covered=3) == 100.0
