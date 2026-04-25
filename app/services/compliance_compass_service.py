"""
Compliance Compass — Fusions-Index aus Readiness + Governance-Workflow-Signalen.

Deterministisch, erklärbar, mandanten-isoliert (kein LLM im MVP; später optional erweiterbar).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, select

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

W_STRATEGIC = 0.38
W_EXEC = 0.27
W_CADENCE = 0.20
W_RES = 0.15


def _clamp_int(n: float | int) -> int:
    return max(0, min(100, int(round(n))))


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


def _strategic_score(session: Session, tenant_id: str) -> tuple[int, str]:
    try:
        rs = compute_readiness_score(session, tenant_id)
        return rs.score, str(rs.level)
    except Exception:  # pragma: no cover - defensiv gegen DB-Edge-Cases
        logger.exception("compliance_compass: readiness failed tenant=%s", tenant_id)
        return 0, "basic"


def _execution_score(
    open_active: int,
    overdue: int,
) -> tuple[int, str]:
    """0–100: niedriger Druck in Backlog & Überfälligkeiten = höher."""
    p_open = min(1.0, open_active / 40.0)
    p_over = min(1.0, overdue / 12.0) if overdue else 0.0
    raw = 100.0 * (1.0 - 0.55 * p_open - 0.45 * p_over)
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
    if hours <= 48:
        s = 92
        detail = f"Letzter Run vor {int(hours)}h — rhythmische Synchronisierung sichtbar."
    elif hours <= 24 * 7:
        s = 78
        detail = "Regel-Sync in den letzten 7 Tagen; Kadenz im normierten Band."
    elif hours <= 24 * 30:
        s = 64
        detail = "Längere Pause seit letztem Lauf; Sync für aktuelle Lage empfohlen."
    else:
        s = 48
        detail = "Letzter abgeschlossener Lauf >30 Tage her; operatives Pulsrisiko."
    return s, detail


def _resilience_score(escalated: int) -> tuple[int, str]:
    s = 100 - min(55, int(escalated) * 9)
    s = _clamp_int(s)
    if escalated == 0:
        detail = "Keine eskalierten Workflow-Tasks im abgefragten Bestand (Status escalated)."
    else:
        detail = f"Eskalierte Tasks: {int(escalated)} — fachlich erhöhter Fokus/Review."
    return s, detail


def _posture(fusion: int) -> str:
    if fusion >= 76:
        return "strong"
    if fusion >= 58:
        return "steady"
    if fusion >= 40:
        return "watch"
    return "elevated"


def _confidence_0_100(
    has_tasks: bool,
    has_runs: bool,
    strategic: int,
    events_24h: int,
) -> int:
    c = 0.58
    if has_tasks:
        c += 0.14
    if has_runs:
        c += 0.14
    if strategic > 0:
        c += 0.10
    if events_24h > 0:
        c += 0.10
    return _clamp_int(c * 100.0)


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


def build_compass_snapshot(
    session: Session,
    tenant_id: str,
) -> ComplianceCompassSnapshotOut:
    now = datetime.now(UTC)
    strategic, level = _strategic_score(session, tenant_id)

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

    # Letzter abgeschlossener Run
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
    if last_c and last_c.tzinfo is None and isinstance(last_c, datetime):
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
    conf = _confidence_0_100(
        has_tasks=has_tasks,
        has_runs=has_runs,
        strategic=strategic,
        events_24h=ev_n,
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
