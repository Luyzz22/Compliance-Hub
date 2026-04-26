"""Unit tests for compliance_compass_service.

Decken ab:
- Confidence-Logik (Min/Max/mittlere Kombinationen, Backward-API).
- Strategic-Score Rollback bei Readiness-Fehler (Codex P1).
- Snapshot-Pipeline bleibt nach Readiness-Fehler nutzbar (kein PendingRollbackError).
- Posture-/Cadence-/Resilience-/Execution-Boundaries (deterministisch, erklärbar).
- Domain-Error + Rollback bei harten DB-Fehlern in der Snapshot-Pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from app.services.compliance_compass_service import (
    ComplianceCompassError,
    _cadence_score,
    _compute_confidence_score,
    _confidence_0_100,
    _ConfidenceSignals,
    _execution_score,
    _posture,
    _resilience_score,
    _strategic_score,
    build_compass_snapshot,
)

# --------------------------------------------------------------------------------------
# Confidence
# --------------------------------------------------------------------------------------


def test_confidence_baseline_is_low_without_signals() -> None:
    assert _confidence_0_100(False, False, 0, 0) == 22


def test_confidence_max_with_all_signals() -> None:
    assert _confidence_0_100(True, True, 1, 3) == 100


def test_confidence_only_readiness_present() -> None:
    """Nur Readiness-Signal → Prior + Readiness-Bonus; deutlich unter Voll-Confidence."""
    val = _confidence_0_100(False, False, 80, 0)
    assert val == round((0.22 + 0.19) * 100)


def test_confidence_tasks_and_runs_no_readiness_no_events() -> None:
    val = _confidence_0_100(True, True, 0, 0)
    assert val == round((0.22 + 0.20 + 0.20) * 100)


def test_compute_confidence_with_named_signals_matches_legacy_api() -> None:
    """Neue interne API muss exakt dieselben Werte liefern wie der Backward-Wrapper."""
    legacy = _confidence_0_100(True, False, 50, 5)
    structured = _compute_confidence_score(
        _ConfidenceSignals(has_tasks=True, has_runs=False, has_readiness=True, has_events=True)
    )
    assert legacy == structured


def test_compute_confidence_distinguishes_readiness_success_from_score() -> None:
    """Wichtig: ein Readiness-Score von 0 bei *erfolgreicher* Berechnung darf
    nicht wie ein Failure aussehen — die strukturierte API erlaubt diese Trennung."""
    failed = _compute_confidence_score(
        _ConfidenceSignals(has_tasks=False, has_runs=False, has_readiness=False, has_events=False)
    )
    succeeded_score_zero = _compute_confidence_score(
        _ConfidenceSignals(has_tasks=False, has_runs=False, has_readiness=True, has_events=False)
    )
    assert succeeded_score_zero > failed


# --------------------------------------------------------------------------------------
# Strategic Score / Rollback
# --------------------------------------------------------------------------------------


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


def test_strategic_score_rolls_back_even_when_rollback_itself_raises() -> None:
    """Sekundäre Rollback-Fehler dürfen den Aufrufer nicht crashen."""
    session = MagicMock()
    session.rollback.side_effect = RuntimeError("rollback failed")
    with patch(
        "app.services.compliance_compass_service.compute_readiness_score",
        side_effect=RuntimeError("transient db"),
    ):
        score, level = _strategic_score(session, "tenant-x")
    assert (score, level) == (0, "basic")


# --------------------------------------------------------------------------------------
# Posture / Cadence / Resilience / Execution Boundaries
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fusion", "expected"),
    [
        (0, "elevated"),
        (39, "elevated"),
        (40, "watch"),
        (57, "watch"),
        (58, "steady"),
        (75, "steady"),
        (76, "strong"),
        (100, "strong"),
    ],
)
def test_posture_thresholds(fusion: int, expected: str) -> None:
    assert _posture(fusion) == expected


def test_cadence_score_is_neutral_when_no_run() -> None:
    s, detail = _cadence_score(None)
    assert s == 50
    assert "neutral" in detail.lower()


@pytest.mark.parametrize(
    ("hours_ago", "expected_score"),
    [
        (1, 92),
        (47, 92),
        (49, 78),
        (24 * 6, 78),
        (24 * 8, 64),
        # Knapp unterhalb der 30-Tage-Grenze (Verarbeitungszeit-Slop tolerieren).
        (24 * 30 - 1, 64),
        (24 * 31, 48),
    ],
)
def test_cadence_score_boundaries(hours_ago: int, expected_score: int) -> None:
    last = datetime.now(UTC) - timedelta(hours=hours_ago)
    s, _ = _cadence_score(last)
    assert s == expected_score


def test_cadence_score_handles_naive_datetime() -> None:
    """Datenbanken liefern teils naive UTC-Stempel (SQLite). Service muss tolerant sein."""
    last = (datetime.now(UTC) - timedelta(hours=2)).replace(tzinfo=None)
    s, _ = _cadence_score(last)
    assert s == 92


@pytest.mark.parametrize(
    ("escalated", "expected"),
    [
        (0, 100),
        (1, 91),
        (5, 55),
        (6, 46),
        (7, 45),
        (50, 45),
    ],
)
def test_resilience_score_boundaries(escalated: int, expected: int) -> None:
    s, _ = _resilience_score(escalated)
    assert s == expected


def test_execution_score_no_pressure_is_perfect() -> None:
    s, _ = _execution_score(0, 0)
    assert s == 100


def test_execution_score_high_pressure_is_floored_at_zero() -> None:
    s, _ = _execution_score(1000, 1000)
    assert s == 0


def test_execution_score_overdue_dominates_even_with_low_open() -> None:
    low_open_high_overdue, _ = _execution_score(0, 50)
    low_open_no_overdue, _ = _execution_score(0, 0)
    assert low_open_high_overdue < low_open_no_overdue


# --------------------------------------------------------------------------------------
# Snapshot Pipeline: Rollback + Domain-Error
# --------------------------------------------------------------------------------------


def test_build_snapshot_raises_compass_error_and_rolls_back_on_db_failure() -> None:
    """Wenn eine harte DB-Exception in der Pipeline auftritt, soll der Service
    die Session rollbacken und einen sauberen Domain-Error werfen — *kein*
    SQLAlchemy-Internalerror nach außen, kein PendingRollbackError danach."""
    session = MagicMock()
    session.execute.side_effect = OperationalError("SELECT 1", {}, Exception("boom"))

    with patch(
        "app.services.compliance_compass_service.compute_readiness_score",
        return_value=MagicMock(score=42, level="managed"),
    ):
        with pytest.raises(ComplianceCompassError):
            build_compass_snapshot(session, "tenant-rolling")

    session.rollback.assert_called()


def test_build_snapshot_keeps_session_usable_after_readiness_failure() -> None:
    """Regressions-Test für Codex P1: nach Readiness-Fehler muss der weitere
    Pipeline-Verlauf normal mit der Session arbeiten können (Rollback fand statt,
    nachfolgende ``session.execute``-Aufrufe laufen ohne PendingRollbackError)."""
    session = MagicMock()

    counters: dict[str, int] = {"calls": 0}

    def _execute_ok(*_args, **_kwargs):
        counters["calls"] += 1
        result = MagicMock()
        result.scalar.return_value = 0
        result.one_or_none.return_value = None
        return result

    session.execute.side_effect = _execute_ok

    with patch(
        "app.services.compliance_compass_service.compute_readiness_score",
        side_effect=RuntimeError("readiness offline"),
    ):
        snapshot = build_compass_snapshot(session, "tenant-resilient")

    # Snapshot wurde gebaut, Rollback fand genau einmal statt (vom strategic-score-Pfad),
    # alle nachfolgenden Queries liefen erfolgreich auf derselben Session.
    session.rollback.assert_called_once()
    assert snapshot.tenant_id == "tenant-resilient"
    assert snapshot.provenance.readiness_score == 0
    assert snapshot.provenance.readiness_level == "basic"
    # Confidence darf bei dünner Datenlage + fehlgeschlagenem Readiness nicht hoch sein.
    assert snapshot.confidence_0_100 <= 30
    # Mind. die Pipeline-Counts (open/escalated/overdue/runs/events/has_tasks) liefen erfolgreich.
    assert counters["calls"] >= 5
