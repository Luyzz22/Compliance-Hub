"""
Deterministische Workflow-Materialisierung (MVP, kein LLM).

Regeln bilden Quellen (Remediation, Controls, Board, Service-Health) auf
`governance_workflow_tasks` ab. Idempotenz über `dedupe_key` pro Mandant.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_db import (
    BoardReportActionTable,
    GovernanceControlEvidenceTable,
    GovernanceControlTable,
    GovernanceWorkflowEventTable,
    GovernanceWorkflowNotificationDeliveryTable,
    GovernanceWorkflowNotificationTable,
    GovernanceWorkflowRunTable,
    GovernanceWorkflowTaskHistoryTable,
    GovernanceWorkflowTaskTable,
    GovernanceWorkflowTemplateTable,
    RemediationActionTable,
    ServiceHealthIncidentTable,
)

RULE_BUNDLE_VERSION = "2026.04.30.mvp1"

# Katalog: wird bei leerer Tabelle befüllt (create_all + kein Migrations-Seed).
_TEMPLATE_CATALOG: list[dict[str, Any]] = [
    {
        "code": "tpl_evidence_gap_high",
        "title": "Evidence-Lücke (hoch)",
        "description": "Nachweis für betroffene Controls beschaffen und verknüpfen.",
        "default_sla_days": 5,
    },
    {
        "code": "tpl_review_due",
        "title": "Control-Review fällig",
        "description": "Geplante oder überfällige Wirksamkeits-/Reife-Beurteilung des Controls.",
        "default_sla_days": 3,
    },
    {
        "code": "tpl_remediation_overdue",
        "title": "Maßnahme nachfassen",
        "description": (
            "Offene Remediation-Maßnahme ist überfällig; Status klären oder Termin anpassen."
        ),
        "default_sla_days": 2,
    },
    {
        "code": "tpl_service_incident",
        "title": "Incident-Response (Betrieb)",
        "description": (
            "Kritische Service-Störung: Beweiskette, Kommunikation, Entstörung dokumentieren."
        ),
        "default_sla_days": 0,
    },
    {
        "code": "tpl_board_action",
        "title": "Board-Follow-up",
        "description": "Umsetzung der Board-Action inkl. Owner, Termin, Nachweis im Audit-Case.",
        "default_sla_days": 7,
    },
]

SOURCE_REMEDIATION = "remediation_action"
SOURCE_CONTROL = "governance_control"
SOURCE_BOARD_ACTION = "board_report_action"
SOURCE_SERVICE_INCIDENT = "service_health_incident"
OPEN_TASK_STATUSES = ("open", "in_progress", "escalated")
# Erlaubte Werte für PATCH / tasks (und gespeicherte Zustände) — alles andere wird abgelehnt
WORKFLOW_TASK_ALLOWED_STATUSES = frozenset(
    {"open", "in_progress", "done", "cancelled", "escalated"}
)


def _now() -> datetime:
    return datetime.now(UTC)


def _remediation_is_overdue(*, status: str, due_at_utc: datetime | None, now: datetime) -> bool:
    if due_at_utc is None or status not in ("open", "in_progress", "blocked"):
        return False
    due = due_at_utc if due_at_utc.tzinfo is not None else due_at_utc.replace(tzinfo=UTC)
    n = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    return due < n


def _task_is_overdue(*, status: str, due_at_utc: datetime | None, now: datetime) -> bool:
    if due_at_utc is None or status not in ("open", "in_progress", "escalated"):
        return False
    due = due_at_utc if due_at_utc.tzinfo is not None else due_at_utc.replace(tzinfo=UTC)
    n = now if now.tzinfo is not None else now.replace(tzinfo=UTC)
    return due < n


async def ensure_workflow_template_catalog(session: AsyncSession) -> None:
    """Idempotent: System-Templates, falls Tabelle (nach create_all) leer ist."""
    n = await session.scalar(
        select(func.count()).select_from(GovernanceWorkflowTemplateTable)  # type: ignore[arg-type]
    )
    if n and n > 0:
        return
    for t in _TEMPLATE_CATALOG:
        session.add(
            GovernanceWorkflowTemplateTable(
                id=str(uuid4()),
                code=t["code"],
                title=t["title"],
                description=t["description"],
                default_sla_days=t["default_sla_days"],
                is_system=1,
            )
        )
    await session.flush()


async def _append_event(
    session: AsyncSession,
    *,
    tenant_id: str,
    event_type: str,
    source_type: str,
    source_id: str,
    message: str,
    severity: str = "info",
    ref_task_id: str | None = None,
    payload: dict[str, Any] | None = None,
    event_tally: list[int] | None = None,
) -> None:
    session.add(
        GovernanceWorkflowEventTable(
            id=str(uuid4()),
            tenant_id=tenant_id,
            at_utc=_now(),
            event_type=event_type,
            severity=severity,
            ref_task_id=ref_task_id,
            source_type=source_type,
            source_id=source_id,
            message=message,
            payload_json=payload or {},
        )
    )
    if event_tally is not None:
        event_tally[0] += 1


async def _task_by_dedupe(
    session: AsyncSession, tenant_id: str, key: str
) -> GovernanceWorkflowTaskTable | None:
    r = await session.scalar(
        select(GovernanceWorkflowTaskTable).where(
            GovernanceWorkflowTaskTable.tenant_id == tenant_id,
            GovernanceWorkflowTaskTable.dedupe_key == key,
        )
    )
    return r


async def _materialize_task(
    session: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    title: str,
    description: str,
    source_type: str,
    source_id: str,
    source_ref: dict[str, Any],
    dedupe_key: str,
    template_code: str,
    assignee: str | None,
    due_at: datetime | None,
    priority: str,
    framework_tags: list[str] | None,
    event_tally: list[int] | None = None,
) -> str | None:
    if await _task_by_dedupe(session, tenant_id, dedupe_key) is not None:
        return None
    now = _now()
    tid = str(uuid4())
    session.add(
        GovernanceWorkflowTaskTable(
            id=tid,
            tenant_id=tenant_id,
            run_id=run_id,
            template_code=template_code,
            title=title,
            description=description,
            status="open",
            priority=priority,
            source_type=source_type,
            source_id=source_id,
            source_ref_json=source_ref,
            assignee_user_id=assignee,
            due_at_utc=due_at,
            framework_tags_json=framework_tags or [],
            dedupe_key=dedupe_key,
            escalation_level=0,
            last_comment=None,
            created_at_utc=now,
            updated_at_utc=now,
            created_by="governance_workflow:rule_sync",
        )
    )
    await session.flush()
    session.add(
        GovernanceWorkflowTaskHistoryTable(
            id=str(uuid4()),
            tenant_id=tenant_id,
            task_id=tid,
            at_utc=now,
            from_status=None,
            to_status="open",
            actor_id="system",
            note="Task deterministisch aus Quelle abgeleitet (MVP-Regel).",
            payload_json={"dedupe_key": dedupe_key},
        )
    )
    await _append_event(
        session,
        tenant_id=tenant_id,
        event_type="task.materialized",
        source_type=source_type,
        source_id=source_id,
        ref_task_id=tid,
        message=title,
        payload={"template_code": template_code, "dedupe_key": dedupe_key},
        event_tally=event_tally,
    )
    return tid


# --- Regel-Mappings (kein KI) -------------------------------------------------


async def _rule_remediation_overdue(
    session: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    now: datetime,
    event_tally: list[int] | None = None,
) -> tuple[int, int]:
    """
    Regel: überfällige open/in_progress/blocked Remediation-Actions
    -> Task "Maßnahme nachfassen" (idempotent pro Action).
    """
    created = 0
    esc_ev = 0
    act_rows = (
        await session.scalars(
            select(RemediationActionTable).where(
                RemediationActionTable.tenant_id == tenant_id,
                RemediationActionTable.status.in_(("open", "in_progress", "blocked")),
            )
        )
    ).all()
    for a in act_rows:
        if not _remediation_is_overdue(status=a.status, due_at_utc=a.due_at_utc, now=now):
            continue
        dk = f"wf:rem:overdue:{a.id}"
        t = await _materialize_task(
            session,
            tenant_id=tenant_id,
            run_id=run_id,
            title=f"Maßnahme nachfassen: {a.title[:200]}",
            description="Remediation ist überfällig; Fälligkeit prüfen oder Frist anpassen.",
            source_type=SOURCE_REMEDIATION,
            source_id=a.id,
            source_ref={"action_title": a.title, "action_status": a.status},
            dedupe_key=dk,
            template_code="tpl_remediation_overdue",
            assignee=a.owner,
            due_at=a.due_at_utc,
            priority="high" if a.priority in ("high", "critical") else a.priority,
            framework_tags=[],
            event_tally=event_tally,
        )
        if t is not None:
            created += 1
        if a.priority in ("critical", "high") and t is not None:
            # Stub-Queue: ein Eintrag pro neu materialisiertem hochkritischem Task (MVP)
            await _append_event(
                session,
                tenant_id=tenant_id,
                event_type="remediation.escalation.suggested",
                source_type=SOURCE_REMEDIATION,
                source_id=a.id,
                severity="warning",
                ref_task_id=t,
                message=("Eskalation (Stub) für hochkritische, überfällige Maßnahme"),
                payload={"queue": "governance_workflow_notification"},
                event_tally=event_tally,
            )
            n_id = str(uuid4())
            session.add(
                GovernanceWorkflowNotificationTable(
                    id=n_id,
                    tenant_id=tenant_id,
                    ref_task_id=t,
                    channel="stub_queue",
                    status="queued",
                    title=f"Eskalation: {a.title[:200]}",
                    body_text=(
                        "Überfällige, hoch priorisierte Maßnahme. E-Mail/n8n folgt in Phase 2."
                    ),
                    created_at_utc=now,
                    payload_json={"rule": "remediation_overdue_high", "action_id": a.id},
                )
            )
            esc_ev += 1
    return created, esc_ev


async def _rule_service_health_incidents(
    session: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    now: datetime,
    event_tally: list[int] | None = None,
) -> int:
    """
    Regel: offener kritische Incident (Betriebs-Monitoring)
    -> genau ein Incident-Response-Task.
    """
    inc_rows = (
        await session.scalars(
            select(ServiceHealthIncidentTable).where(
                ServiceHealthIncidentTable.tenant_id == tenant_id,
                ServiceHealthIncidentTable.incident_state == "open",
                ServiceHealthIncidentTable.severity == "critical",
            )
        )
    ).all()
    c = 0
    for inc in inc_rows:
        dk = f"wf:health:incident:{inc.id}"
        t = await _materialize_task(
            session,
            tenant_id=tenant_id,
            run_id=run_id,
            title=f"Incident-Response: {inc.title[:200]}",
            description=inc.summary[:2000] if inc.summary else inc.title,
            source_type=SOURCE_SERVICE_INCIDENT,
            source_id=inc.id,
            source_ref={"service_name": inc.service_name, "severity": inc.severity},
            dedupe_key=dk,
            template_code="tpl_service_incident",
            assignee=None,
            due_at=now,
            priority="critical",
            framework_tags=["ISO_27001", "NIS2_OPERATIONS"],
            event_tally=event_tally,
        )
        if t is not None:
            c += 1
    return c


async def _rule_board_actions(
    session: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    now: datetime,
    event_tally: list[int] | None = None,
) -> int:
    """
    Regel: offene Board-Action -> Follow-up-Task mit Due/Owner.
    """
    act_rows = (
        await session.scalars(
            select(BoardReportActionTable).where(
                BoardReportActionTable.tenant_id == tenant_id,
                BoardReportActionTable.status == "open",
            )
        )
    ).all()
    c = 0
    for b in act_rows:
        dk = f"wf:board:action:{b.id}"
        d = b.due_at
        t = await _materialize_task(
            session,
            tenant_id=tenant_id,
            run_id=run_id,
            title=f"Board-Follow-up: {b.action_title[:200]}",
            description=(b.action_detail or "")[:4000],
            source_type=SOURCE_BOARD_ACTION,
            source_id=b.id,
            source_ref={"report_id": b.report_id, "priority": b.priority},
            dedupe_key=dk,
            template_code="tpl_board_action",
            assignee=b.owner,
            due_at=d,
            priority=b.priority,
            framework_tags=[],
            event_tally=event_tally,
        )
        if t is not None:
            c += 1
    return c


async def _control_ids_with_evidence(session: AsyncSession, tenant_id: str) -> set[str]:
    r = await session.scalars(
        select(GovernanceControlEvidenceTable.control_id)
        .where(GovernanceControlEvidenceTable.tenant_id == tenant_id)
        .distinct()
    )
    return {x for x in r.all()}


async def _rule_evidence_gaps(
    session: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    now: datetime,
    event_tally: list[int] | None = None,
) -> int:
    """
    Regel: Control ohne Evidence-Artefakt, Status noch nicht abgeschlossen
    -> Task "Evidence beschaffen" (Hinweis auf Audit-Readiness).
    """
    with_ev = await _control_ids_with_evidence(session, tenant_id)
    stmt = select(GovernanceControlTable).where(
        GovernanceControlTable.tenant_id == tenant_id,
        GovernanceControlTable.status.in_(("not_started", "in_progress")),
    )
    if with_ev:
        stmt = stmt.where(GovernanceControlTable.id.not_in(list(with_ev)))
    rows = (await session.scalars(stmt)).all()
    c = 0
    for g in rows:
        dk = f"wf:ctrl:evidence_gap:{g.id}"
        d = now + timedelta(days=3)  # MVP: fester Puffer, später aus `default_sla` am Template
        t = await _materialize_task(
            session,
            tenant_id=tenant_id,
            run_id=run_id,
            title=f"Evidence beschaffen: {g.title[:200]}",
            description="Für den Control fehlt noch mindestens ein verknüpfter Nachweis.",
            source_type=SOURCE_CONTROL,
            source_id=g.id,
            source_ref={"control_status": g.status},
            dedupe_key=dk,
            template_code="tpl_evidence_gap_high",
            assignee=g.owner,
            due_at=d,
            priority="high",
            framework_tags=(g.framework_tags_json or []) if g.framework_tags_json else [],
            event_tally=event_tally,
        )
        if t is not None:
            c += 1
    return c


async def _rule_overdue_reviews(
    session: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    now: datetime,
    event_tally: list[int] | None = None,
) -> int:
    """
    Regel: next_review_at in der Vergangenheit -> "Review durchführen".
    """
    rows = (
        await session.scalars(
            select(GovernanceControlTable).where(
                GovernanceControlTable.tenant_id == tenant_id,
                GovernanceControlTable.next_review_at.is_not(None),  # noqa: E711
                GovernanceControlTable.next_review_at < now,
                GovernanceControlTable.status.in_(
                    ("not_started", "in_progress", "in_review", "not_applicable")
                ),
            )
        )
    ).all()
    c = 0
    for g in rows:
        r_at = g.next_review_at
        if r_at is None:
            continue
        dk = f"wf:ctrl:review_due:{g.id}"
        t = await _materialize_task(
            session,
            tenant_id=tenant_id,
            run_id=run_id,
            title=f"Review durchführen: {g.title[:200]}",
            description="Periodisches Review fällig oder überfällig (UTC next_review_at).",
            source_type=SOURCE_CONTROL,
            source_id=g.id,
            source_ref={"next_review_at": r_at.isoformat()},
            dedupe_key=dk,
            template_code="tpl_review_due",
            assignee=g.owner,
            due_at=r_at,
            priority="high",
            framework_tags=(g.framework_tags_json or []) if g.framework_tags_json else [],
            event_tally=event_tally,
        )
        if t is not None:
            c += 1
    return c


# --- Public API (Services) ----------------------------------------------------


async def run_deterministic_sync(
    session: AsyncSession, tenant_id: str, rule_profile: str
) -> dict[str, int | str]:
    """
    Ein synchroner Durchlauf: Run anlegen, Regeln in fester Reihenfolge, Statistik im Run.
    """
    await ensure_workflow_template_catalog(session)
    if rule_profile != "default":
        raise ValueError("Nur 'default' im MVP (Profile sind Phase-2-Extension).")
    now = _now()
    run_id = str(uuid4())
    run = GovernanceWorkflowRunTable(
        id=run_id,
        tenant_id=tenant_id,
        trigger_mode="rule_sync",
        status="running",
        rule_bundle_version=RULE_BUNDLE_VERSION,
        summary_json={},
        started_at_utc=now,
        completed_at_utc=None,
    )
    session.add(run)
    await session.flush()
    event_tally: list[int] = [0]
    t1, n_esc = await _rule_remediation_overdue(
        session,
        tenant_id=tenant_id,
        run_id=run_id,
        now=now,
        event_tally=event_tally,
    )
    t2 = await _rule_service_health_incidents(
        session,
        tenant_id=tenant_id,
        run_id=run_id,
        now=now,
        event_tally=event_tally,
    )
    t3 = await _rule_board_actions(
        session,
        tenant_id=tenant_id,
        run_id=run_id,
        now=now,
        event_tally=event_tally,
    )
    t4 = await _rule_evidence_gaps(
        session,
        tenant_id=tenant_id,
        run_id=run_id,
        now=now,
        event_tally=event_tally,
    )
    t5 = await _rule_overdue_reviews(
        session,
        tenant_id=tenant_id,
        run_id=run_id,
        now=now,
        event_tally=event_tally,
    )
    mat = t1 + t2 + t3 + t4 + t5
    ev_n = int(event_tally[0])
    end = _now()
    run.status = "completed"
    run.completed_at_utc = end
    run.summary_json = {
        "tasks_materialized": mat,
        "remediation_overdue": t1,
        "service_incidents": t2,
        "board_actions": t3,
        "evidence_gaps": t4,
        "overdue_reviews": t5,
        "remediation_notification_events": n_esc,
        "events_written": ev_n,
    }
    await session.flush()
    return {
        "run_id": run_id,
        "status": "completed",
        "tasks_materialized": mat,
        "events_written": ev_n,
        "notifications_queued": n_esc,
        "rule_bundle_version": RULE_BUNDLE_VERSION,
    }


async def compute_kpis(
    session: AsyncSession, tenant_id: str, now: datetime | None = None
) -> dict[str, int]:
    n = now or _now()
    open_c = int(
        await session.scalar(
            select(func.count())
            .select_from(GovernanceWorkflowTaskTable)
            .where(
                GovernanceWorkflowTaskTable.tenant_id == tenant_id,
                GovernanceWorkflowTaskTable.status.in_(OPEN_TASK_STATUSES),
            )
        )
        or 0
    )
    t_rows: Sequence = (
        await session.scalars(
            select(GovernanceWorkflowTaskTable).where(
                GovernanceWorkflowTaskTable.tenant_id == tenant_id,
                GovernanceWorkflowTaskTable.status.in_(OPEN_TASK_STATUSES),
            )
        )
    ).all() or []
    od = 0
    for r in t_rows:
        if _task_is_overdue(status=r.status, due_at_utc=r.due_at_utc, now=n):
            od += 1
    esc = int(
        await session.scalar(
            select(func.count())
            .select_from(GovernanceWorkflowTaskTable)
            .where(
                GovernanceWorkflowTaskTable.tenant_id == tenant_id,
                or_(
                    GovernanceWorkflowTaskTable.status == "escalated",
                    GovernanceWorkflowTaskTable.escalation_level > 0,
                ),
            )
        )
        or 0
    )
    n_queued = int(
        await session.scalar(
            select(func.count())
            .select_from(GovernanceWorkflowNotificationTable)
            .where(
                GovernanceWorkflowNotificationTable.tenant_id == tenant_id,
                GovernanceWorkflowNotificationTable.status == "queued",
            )
        )
        or 0
    )
    w24h = n - timedelta(hours=24)
    ev_24h = int(
        await session.scalar(
            select(func.count())
            .select_from(GovernanceWorkflowEventTable)
            .where(
                GovernanceWorkflowEventTable.tenant_id == tenant_id,
                GovernanceWorkflowEventTable.at_utc >= w24h,
            )
        )
        or 0
    )
    return {
        "open_tasks": open_c,
        "overdue_tasks": od,
        "escalated_tasks": esc,
        "notifications_queued": n_queued,
        "workflow_events_24h": ev_24h,
    }


async def list_runs(
    session: AsyncSession, tenant_id: str, limit: int = 20
) -> list[GovernanceWorkflowRunTable]:
    rows = (
        await session.scalars(
            select(GovernanceWorkflowRunTable)
            .where(GovernanceWorkflowRunTable.tenant_id == tenant_id)
            .order_by(desc(GovernanceWorkflowRunTable.started_at_utc))
            .limit(limit)
        )
    ).all()
    return list(rows)


async def list_tasks_for_tenant(
    session: AsyncSession,
    tenant_id: str,
    *,
    status: str | None = None,
    source_type: str | None = None,
    assignee: str | None = None,
    framework_tag: str | None = None,
    priority: str | None = None,
    limit: int = 200,
) -> list[GovernanceWorkflowTaskTable]:
    stmt = select(GovernanceWorkflowTaskTable).where(
        GovernanceWorkflowTaskTable.tenant_id == tenant_id
    )
    if status:
        stmt = stmt.where(GovernanceWorkflowTaskTable.status == status)
    if source_type:
        stmt = stmt.where(GovernanceWorkflowTaskTable.source_type == source_type)
    if assignee:
        stmt = stmt.where(GovernanceWorkflowTaskTable.assignee_user_id == assignee)
    if priority:
        stmt = stmt.where(GovernanceWorkflowTaskTable.priority == priority)
    if framework_tag:
        stmt = stmt.where(
            GovernanceWorkflowTaskTable.framework_tags_json.like(f"%{framework_tag}%")
        )
    stmt = stmt.order_by(desc(GovernanceWorkflowTaskTable.updated_at_utc)).limit(limit)
    r = (await session.scalars(stmt)).all()
    return list(r)


async def get_task(
    session: AsyncSession, tenant_id: str, task_id: str
) -> GovernanceWorkflowTaskTable | None:
    return await session.scalar(
        select(GovernanceWorkflowTaskTable).where(
            GovernanceWorkflowTaskTable.tenant_id == tenant_id,
            GovernanceWorkflowTaskTable.id == task_id,
        )
    )


async def list_task_history(
    session: AsyncSession, tenant_id: str, task_id: str
) -> list[GovernanceWorkflowTaskHistoryTable]:
    return list(
        (
            await session.scalars(
                select(GovernanceWorkflowTaskHistoryTable)
                .where(
                    GovernanceWorkflowTaskHistoryTable.tenant_id == tenant_id,
                    GovernanceWorkflowTaskHistoryTable.task_id == task_id,
                )
                .order_by(GovernanceWorkflowTaskHistoryTable.at_utc)
            )
        ).all()
    )


async def list_events(
    session: AsyncSession, tenant_id: str, limit: int = 100
) -> list[GovernanceWorkflowEventTable]:
    return list(
        (
            await session.scalars(
                select(GovernanceWorkflowEventTable)
                .where(GovernanceWorkflowEventTable.tenant_id == tenant_id)
                .order_by(desc(GovernanceWorkflowEventTable.at_utc))
                .limit(limit)
            )
        ).all()
    )


async def list_notifications(
    session: AsyncSession, tenant_id: str, limit: int = 100
) -> list[GovernanceWorkflowNotificationTable]:
    return list(
        (
            await session.scalars(
                select(GovernanceWorkflowNotificationTable)
                .where(GovernanceWorkflowNotificationTable.tenant_id == tenant_id)
                .order_by(desc(GovernanceWorkflowNotificationTable.created_at_utc))
                .limit(limit)
            )
        ).all()
    )


async def list_notification_deliveries(
    session: AsyncSession, tenant_id: str, limit: int = 100
) -> list[GovernanceWorkflowNotificationDeliveryTable]:
    return list(
        (
            await session.scalars(
                select(GovernanceWorkflowNotificationDeliveryTable)
                .where(GovernanceWorkflowNotificationDeliveryTable.tenant_id == tenant_id)
                .order_by(desc(GovernanceWorkflowNotificationDeliveryTable.delivered_at_utc))
                .limit(limit)
            )
        ).all()
    )


async def list_template_rows(
    session: AsyncSession,
) -> list[GovernanceWorkflowTemplateTable]:
    await ensure_workflow_template_catalog(session)
    return list((await session.scalars(select(GovernanceWorkflowTemplateTable))).all())


async def create_test_notification(
    session: AsyncSession,
    tenant_id: str,
    *,
    channel: str,
    title: str,
    body: str,
    ref_task_id: str | None,
) -> tuple[str, str]:
    now = _now()
    n_id = str(uuid4())
    d_id = str(uuid4())
    if ref_task_id:
        t = await get_task(session, tenant_id, ref_task_id)
        if t is None:
            raise KeyError("task not found")
    session.add(
        GovernanceWorkflowNotificationTable(
            id=n_id,
            tenant_id=tenant_id,
            ref_task_id=ref_task_id,
            channel=channel,
            status="test_record",
            title=title,
            body_text=body,
            created_at_utc=now,
            payload_json={"source": "manual_test"},
        )
    )
    await session.flush()
    session.add(
        GovernanceWorkflowNotificationDeliveryTable(
            id=d_id,
            tenant_id=tenant_id,
            notification_id=n_id,
            channel=channel,
            result="ok",
            detail="MVP: no external transport; record only.",
            delivered_at_utc=now,
            payload_json={},
        )
    )
    await session.flush()
    return n_id, d_id


async def update_workflow_task(
    session: AsyncSession,
    tenant_id: str,
    task_id: str,
    *,
    status: str | None,
    assignee_user_id: str | None,
    assignee_explicit: bool = False,
    last_comment: str | None,
    actor_id: str,
) -> GovernanceWorkflowTaskTable:
    t = await get_task(session, tenant_id, task_id)
    if t is None:
        raise KeyError("not_found")
    now = _now()
    before = t.status
    if status is not None:
        if status not in WORKFLOW_TASK_ALLOWED_STATUSES:
            raise ValueError("invalid_workflow_task_status")
        t.status = status
    if assignee_explicit:
        t.assignee_user_id = assignee_user_id
    if last_comment is not None:
        t.last_comment = last_comment
    if t.status == "escalated":
        t.escalation_level = max(1, t.escalation_level)
    t.updated_at_utc = now
    session.add(
        GovernanceWorkflowTaskHistoryTable(
            id=str(uuid4()),
            tenant_id=tenant_id,
            task_id=t.id,
            at_utc=now,
            from_status=before,
            to_status=t.status,
            actor_id=actor_id,
            note=last_comment,
            payload_json={},
        )
    )
    await _append_event(
        session,
        tenant_id=tenant_id,
        event_type="task.updated",
        source_type="governance_workflow_task",
        source_id=t.id,
        ref_task_id=t.id,
        message=f"Status {before} -> {t.status}",
        payload={"actor": actor_id},
    )
    await session.flush()
    return t
