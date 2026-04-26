"""Unit tests for compliance_compass_service (Codex: rollback, confidence prior)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.compliance_compass_service import _confidence_0_100, _strategic_score


def test_confidence_baseline_is_low_without_signals() -> None:
    assert _confidence_0_100(False, False, 0, 0) == 22


def test_confidence_max_with_all_signals() -> None:
    assert _confidence_0_100(True, True, 1, 3) == 100


def test_strategic_score_rollback_after_readiness_failure() -> None:
    session = MagicMock()
    with patch(
        "app.services.compliance_compass_service.compute_readiness_score",
        side_effect=RuntimeError("transient db"),
    ):
        score, level = _strategic_score(session, "tenant-a")
    assert score == 0
    assert level == "basic"
    session.rollback.assert_called_once()
