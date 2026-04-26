"""
Compliance Compass — Fusions-Index aus Readiness + Governance-Workflow-Signalen.

Deterministisch, erklärbar, mandanten-isoliert (kein LLM im MVP; später optional erweiterbar).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, select
from sqlalchemy.exc import SQLAlchemyError

from app.compliance_compass_models import (
    COMPASS_VERSION,
    CompassPillarKey,
    CompassPillarOut,
    CompassProvenanceOut,
    ComplianceCompassSnapshotOut,
)
from app.models_db import (
    GovernanceWorkflowEventTable,
    GovernanceWorkflowRunTable,
    GovernanceWorkflowTaskTable,
)
from app.services.governance_workflow_service import OPEN_TASK_STATUSES
from app.services.readiness_score_service import compute_readiness_score

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ComplianceCompassError(RuntimeError):
    """Domain-Fehler, wenn der Compass-Snapshot wegen DB-/Infra-Problemen nicht gebaut werden kann.

    Wird vom Router auf 503 abgebildet. Enthält *keine* tenant-spezifischen Details
    (kein Leaky Abstraction nach außen), die volle Kontextkette steht in den Logs.
    """


# Pillar-Gewichte (Summe = 1.0); siehe docs/governance-workflows.md
W_STRATEGIC = 0.38
W_EXEC = 0.27
W_CADENCE = 0.20
W_RES = 0.15

# Confidence-Modell: Prior + bounded Boni. Niedrig wenn Mandant ohne Signale.
# Werte addieren sich auf 1.0 (0.22 + 4×~0.195) und werden zusätzlich durch min(1.0, …) gekappt.
_CONFIDENCE_PRIOR = 0.22
_CONFIDENCE_BONUS_TASKS = 0.20
_CONFIDENCE_BONUS_RUNS = 0.20
_CONFIDENCE_BONUS_READINESS = 0.19
_CONFIDENCE_BONUS_EVENTS = 0.19

# Posture-Schwellen (deterministisch, dokumentiert).
_POSTURE_STRONG = 76
_POSTURE_STEADY = 58
_POSTURE_WATCH = 40

# Cadence-Schwellen (in Stunden).
_CADENCE_HOT_HOURS = 48
_CADENCE_WEEK_HOURS = 24 * 7
_CADENCE_MONTH_HOURS = 24 * 30

# Execution-Druckpunkte (siehe Tests für Boundary-Verhalten).
_EXEC_OPEN_CAP = 40.0
_EXEC_OVERDUE_CAP = 12.0
_EXEC_W_OPEN = 0.55
_EXEC_W_OVERDUE = 0.45

# Resilience-Strafen pro eskaliertem Task (max 55 Punkte Abzug).
_RES_PENALTY_PER_ESCALATED = 9
_RES_MAX_PENALTY = 55


@dataclass(frozen=True, slots=True)
class _ConfidenceSignals:
    """Deterministische, getestete Eingangsgrößen der Confidence-Berechnung."""

    has_tasks: bool
    has_runs: bool
    has_readiness: bool
    has_events: bool


def _clamp_int(n: float | int) -> int:
    return max(0, min(100, int(round(n))))


def _safe_rollback(session: Session, *, reason: str, tenant_id: str) -> None:
    """Rollbackt die Session defensiv und protokolliert auf WARN-Level.

    Schluckt sekundäre Rollback-Fehler bewusst, um den Hauptfehlerpfad nicht zu maskieren.
    """
    try:
        session.rollback()
        logger.warning(
            "compliance_compass.session_rollback reason=%s tenant=%s",
            reason,
            tenant_id,
        )
    except Exception:  # pragma: no cover - sekundärer Fehler nur loggen
        logger.exception(
            "compliance_compass.rollback_failed reason=%s tenant=%s",
            reason,
            tenant_id,
        )


def _count_tasks(session: Session, tenant_id: str, *extra) -> int:
    q = (
        select(func.count())
        .select_from(GovernanceWorkflowTaskTable)
        .where(
            GovernanceWorkflowTaskTable.tenant_id == tenant_id,
            *extra,
        )
    )
    r = session.execute(q)
    return int(r.scalar() or 0)


@dataclass(frozen=True, slots=True)
class _StrategicSignal:
    score: int
    level: str
    success: bool


def _strategic_score(session: Session, tenant_id: str) -> tuple[int, str]:
    """Backward-kompatible Signatur. Intern delegiert an :func:`_strategic_signal`."""
    s = _strategic_signal(session, tenant_id)
    return s.score, s.level


def _strategic_signal(session: Session, tenant_id: str) -> _StrategicSignal:
    """Liefert Readiness-Score + Level + Erfolgsflag.

    Bei Fehler in :func:`compute_readiness_score` wird die Session zurückgerollt,
    damit nachfolgende Queries nicht in ``PendingRollbackError`` laufen, und ein
    neutraler "basic"-Fallback geliefert (graceful degradation).
    """
    try:
        rs = compute_readiness_score(session, tenant_id)
        return _StrategicSignal(score=rs.score, level=str(rs.level), success=True)
    except Exception:
        logger.exception(
            "compliance_compass.readiness_failed tenant=%s",
            tenant_id,
        )
        _safe_rollback(session, reason="readiness_failed", tenant_id=tenant_id)
        return _StrategicSignal(score=0, level="basic", success=False)


def _execution_score(
    open_active: int,
    overdue: int,
) -> tuple[int, str]:
    """0–100: niedriger Druck in Backlog & Überfälligkeiten = höher."""
    p_open = min(1.0, open_active / _EXEC_OPEN_CAP)
    p_over = min(1.0, overdue / _EXEC_OVERDUE_CAP) if overdue else 0.0
    raw = 100.0 * (1.0 - _EXEC_W_OPEN * p_open - _EXEC_W_OVERDUE * p_over)
    detail = f"Offen/aktiv: {open_active}; überfällig: {overdue}."
    return _clamp_int(raw), detail


def _cadence_score(
    last_completed: datetime | None,
) -> tuple[int, str]:
    if last_completed is None:
        return 50, "Noch kein abgeschlossener Regel-Sync im Sichtfenster (neutral)."
    now = datetime.now(UTC)
    if last_completed.tzinfo is None:
        last_completed = last_completed.replace(tzinfo=UTC)
    delta: timedelta = now - last_completed
    hours = delta.total_seconds() / 3600.0
    if hours <= _CADENCE_HOT_HOURS:
        s = 92
        detail = f"Letzter Run vor {int(hours)}h — rhythmische Synchronisierung sichtbar."
    elif hours <= _CADENCE_WEEK_HOURS:
        s = 78
        detail = "Regel-Sync in den letzten 7 Tagen; Kadenz im normierten Band."
    elif hours <= _CADENCE_MONTH_HOURS:
        s = 64
        detail = "Längere Pause seit letztem Lauf; Sync für aktuelle Lage empfohlen."
    else:
        s = 48
        detail = "Letzter abgeschlossener Lauf >30 Tage her; operatives Pulsrisiko."
    return s, detail


def _resilience_score(escalated: int) -> tuple[int, str]:
    s = 100 - min(_RES_MAX_PENALTY, int(escalated) * _RES_PENALTY_PER_ESCALATED)
    s = _clamp_int(s)
    if escalated == 0:
        detail = "Keine eskalierten Workflow-Tasks im abgefragten Bestand (Status escalated)."
    else:
        detail = f"Eskalierte Tasks: {int(escalated)} — fachlich erhöhter Fokus/Review."
    return s, detail


def _posture(fusion: int) -> str:
    if fusion >= _POSTURE_STRONG:
        return "strong"
    if fusion >= _POSTURE_STEADY:
        return "steady"
    if fusion >= _POSTURE_WATCH:
        return "watch"
    return "elevated"


def _compute_confidence_score(signals: _ConfidenceSignals) -> int:
    """Reine, getestete Confidence-Logik (ohne DB-Zugriff).

    Niedriger Prior, kappt bei 1.0. Jeder Boolean ist ein binäres Signal,
    das durch oberhalb dieser Funktion ermittelte Schwellen abgeleitet wird.
    """
    c = _CONFIDENCE_PRIOR
    if signals.has_tasks:
        c += _CONFIDENCE_BONUS_TASKS
    if signals.has_runs:
        c += _CONFIDENCE_BONUS_RUNS
    if signals.has_readiness:
        c += _CONFIDENCE_BONUS_READINESS
    if signals.has_events:
        c += _CONFIDENCE_BONUS_EVENTS
    return _clamp_int(min(1.0, c) * 100.0)


def _confidence_0_100(
    has_tasks: bool,
    has_runs: bool,
    strategic: int,
    events_24h: int,
) -> int:
    """Public, backward-kompatible API; delegiert an :func:`_compute_confidence_score`.

    ``strategic > 0`` wird als "Readiness vorhanden" interpretiert; Aufrufer mit
    expliziter Erfolgsinformation sollten direkt :class:`_ConfidenceSignals` bauen.
    """
    return _compute_confidence_score(
        _ConfidenceSignals(
            has_tasks=bool(has_tasks),
            has_runs=bool(has_runs),
            has_readiness=int(strategic) > 0,
            has_events=int(events_24h) > 0,
        )
    )


def _narrative(
    fusion: int,
    pillars: list[CompassPillarOut],
    posture: str,
) -> str:
    p_map = {p.key: p for p in pillars}
    weakest = min(pillars, key=lambda x: x.score_0_100) if pillars else None
    strongest = max(pillars, key=lambda x: x.score_0_100) if pillars else None
    posture_de = {
        "strong": "in einem überwiegend stabilen Korridor",
        "steady": "solide, mit klarer Verbesserung möglich",
        "watch": "mit sichtbaren Reibflächen",
        "elevated": "mit erhöhtem Steuerungsbedarf",
    }.get(posture, "")

    base = f"Der Compliance-Kompass-Fusionsindex: {fusion}/100 — {posture_de}."
    if not weakest or not strongest:
        return base
    if weakest.key == strongest.key:
        return f"{base} Detaillierte Hebel: Siehe Säulen-Scores."
    st = p_map[strongest.key]
    hebel = f"Größter Hebel: {weakest.label_de} ({weakest.score_0_100})."
    stärke = f"Stärkste: {st.label_de} ({st.score_0_100})."
    return f"{base} {stärke} {hebel}"


def _build_snapshot_unsafe(
    session: Session,
    tenant_id: str,
) -> ComplianceCompassSnapshotOut:
    """Eigentliche Snapshot-Berechnung. Wirft DB-/Infra-Fehler nach oben.

    Wird ausschließlich aus :func:`build_compass_snapshot` aufgerufen, das
    Transaction-Handling und Domain-Error-Mapping kapselt.
    """
    now = datetime.now(UTC)
    strategic_sig = _strategic_signal(session, tenant_id)
    strategic = strategic_sig.score
    level = strategic_sig.level

    openish = _count_tasks(
        session,
        tenant_id,
        GovernanceWorkflowTaskTable.status.in_(list(OPEN_TASK_STATUSES)),
    )
    escalated_n = _count_tasks(
        session,
        tenant_id,
        GovernanceWorkflowTaskTable.status == "escalated",
    )
    overdue = _count_tasks(
        session,
        tenant_id,
        and_(
            GovernanceWorkflowTaskTable.status.in_(list(OPEN_TASK_STATUSES)),
            GovernanceWorkflowTaskTable.due_at_utc.isnot(None),
            GovernanceWorkflowTaskTable.due_at_utc < now,
        ),
    )

    exec_s, exec_detail = _execution_score(openish, overdue)
    res_s, res_detail = _resilience_score(escalated_n)

    run_row = session.execute(
        select(
            GovernanceWorkflowRunTable.completed_at_utc,
            GovernanceWorkflowRunTable.rule_bundle_version,
        )
        .where(
            GovernanceWorkflowRunTable.tenant_id == tenant_id,
            GovernanceWorkflowRunTable.status == "completed",
        )
        .order_by(GovernanceWorkflowRunTable.started_at_utc.desc())
        .limit(1)
    ).one_or_none()
    last_c = run_row[0] if run_row else None
    last_ver = (run_row[1] or "") if run_row else ""
    if last_c and isinstance(last_c, datetime) and last_c.tzinfo is None:
        last_c = last_c.replace(tzinfo=UTC)
    has_runs = run_row is not None
    cad_s, cad_detail = _cadence_score(last_c)

    since = now - timedelta(hours=24)
    ev_n = int(
        session.execute(
            select(func.count())
            .select_from(GovernanceWorkflowEventTable)
            .where(
                GovernanceWorkflowEventTable.tenant_id == tenant_id,
                GovernanceWorkflowEventTable.at_utc >= since,
            )
        ).scalar()
        or 0
    )
    has_tasks = (
        int(
            session.execute(
                select(func.count())
                .select_from(GovernanceWorkflowTaskTable)
                .where(GovernanceWorkflowTaskTable.tenant_id == tenant_id)
            ).scalar()
            or 0
        )
        > 0
    )

    fusion_01 = (
        W_STRATEGIC * (strategic / 100.0)
        + W_EXEC * (exec_s / 100.0)
        + W_CADENCE * (cad_s / 100.0)
        + W_RES * (res_s / 100.0)
    )
    fusion = _clamp_int(fusion_01 * 100.0)
    posture = _posture(fusion)
    conf = _compute_confidence_score(
        _ConfidenceSignals(
            has_tasks=has_tasks,
            has_runs=has_runs,
            has_readiness=strategic_sig.success,
            has_events=ev_n > 0,
        )
    )

    pillars = [
        CompassPillarOut(
            key=CompassPillarKey.STRATEGIC_MATURITY,
            label_de="Strategische Reife (Readiness)",
            score_0_100=strategic,
            weight_in_fusion=W_STRATEGIC,
            detail_de=f"Gewichteter AI- & Compliance-Readiness-Score: {strategic} (Level {level}).",
        ),
        CompassPillarOut(
            key=CompassPillarKey.EXECUTION_FIDELITY,
            label_de="Exekutions- & Backlog-Integrität",
            score_0_100=exec_s,
            weight_in_fusion=W_EXEC,
            detail_de=exec_detail,
        ),
        CompassPillarOut(
            key=CompassPillarKey.OPERATIONAL_CADENCE,
            label_de="Operative Kadenz (Regel-Sync)",
            score_0_100=cad_s,
            weight_in_fusion=W_CADENCE,
            detail_de=cad_detail,
        ),
        CompassPillarOut(
            key=CompassPillarKey.CONTROL_RESILIENCE,
            label_de="Eskalations- & Lage-Bandbreite",
            score_0_100=res_s,
            weight_in_fusion=W_RES,
            detail_de=res_detail,
        ),
    ]

    provenance = CompassProvenanceOut(
        readiness_score=strategic,
        readiness_level=level,
        workflow_open_or_active=openish,
        workflow_overdue=overdue,
        workflow_escalated=escalated_n,
        workflow_events_24h=ev_n,
        last_run_completed_at_utc=last_c,
        rule_bundle_version_last_run=last_ver,
    )

    return ComplianceCompassSnapshotOut(
        tenant_id=tenant_id,
        as_of_utc=now,
        model_version=COMPASS_VERSION,
        fusion_index_0_100=fusion,
        confidence_0_100=conf,
        posture=posture,
        narrative_de=_narrative(fusion, pillars, posture),
        pillars=pillars,
        provenance=provenance,
    )


def build_compass_snapshot(
    session: Session,
    tenant_id: str,
) -> ComplianceCompassSnapshotOut:
    """Baut den Compass-Snapshot mit hartem Transaction-Schutz.

    Bei jeder unerwarteten DB-Exception wird die Session zurückgerollt, damit
    nachfolgende Requests im selben Worker keine ``PendingRollbackError`` sehen.
    Eine technische Fehlermeldung wird in den Logs hinterlegt; nach außen wird
    eine generische :class:`ComplianceCompassError` propagiert (kein Leaking
    interner Details, kein PII).
    """
    try:
        return _build_snapshot_unsafe(session, tenant_id)
    except SQLAlchemyError as exc:
        logger.exception(
            "compliance_compass.snapshot_db_failed tenant=%s exc_type=%s",
            tenant_id,
            type(exc).__name__,
        )
        _safe_rollback(session, reason="snapshot_db_failed", tenant_id=tenant_id)
        raise ComplianceCompassError("compass_snapshot_unavailable") from exc
