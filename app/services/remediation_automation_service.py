"""Deterministische Remediation-Automation: Eskalationen, Reminder, Events — kein LLM."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models_db import (
    BoardReportActionTable,
    BoardReportTable,
    GovernanceControlEvidenceTable,
    GovernanceControlTable,
    RemediationActionEventTable,
    RemediationActionLinkTable,
    RemediationActionTable,
    RemediationAutomationRunTable,
    RemediationEscalationTable,
    RemediationReminderTable,
    ServiceHealthIncidentTable,
)
from app.services.remediation_actions_service import (
    ENTITY_BOARD_REPORT_ACTION,
    generate_remediation_actions,
)

ACTIVE = ("open", "in_progress", "blocked")
REASON_OVERDUE = "DUE_DATE_OVERDUE"
REASON_SEVERE = "CRITICAL_OVERDUE_7D"
REASON_BOARD_PERIOD = "BOARD_ACTION_PERIOD_EXCEEDED"
REASON_EVIDENCE = "EVIDENCE_GAP_HIGH_PRIORITY"
EVENT_ESCALATION = "escalation_created"
EVENT_REMINDER = "reminder_upserted"
EVENT_RECOMMENDATION = "recommendation"
REASON_INCIDENT = "CRITICAL_INCIDENT_UNLINKED_REMEDIATION"


@dataclass
class AutomationRunResult:
    run_id: str
    escalations_created: int = 0
    reminders_upserted: int = 0
    events_written: int = 0
    generated_actions: int = 0
    rule_keys: list[str] = field(default_factory=list)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


async def _open_escalation_exists(
    session: AsyncSession, tenant_id: str, action_id: str, reason: str
) -> bool:
    r = await session.scalar(
        select(RemediationEscalationTable.id).where(
            RemediationEscalationTable.tenant_id == tenant_id,
            RemediationEscalationTable.action_id == action_id,
            RemediationEscalationTable.reason_code == reason,
            RemediationEscalationTable.status == "open",
        )
    )
    return r is not None


def _is_overdue_work_item(status: str, due: datetime | None, now: datetime) -> bool:
    if due is None or status not in ACTIVE:
        return False
    return _aware(due) < now


async def _write_event(
    session: AsyncSession,
    tenant_id: str,
    run_id: str,
    event_type: str,
    action_id: str | None,
    payload: dict[str, object],
) -> None:
    session.add(
        RemediationActionEventTable(
            id=str(uuid4()),
            tenant_id=tenant_id,
            action_id=action_id,
            run_id=run_id,
            event_type=event_type,
            payload_json=json.dumps(payload, ensure_ascii=False, default=str),
            created_at_utc=datetime.now(UTC),
        )
    )


async def run_remediation_automation(
    session: AsyncSession,
    *,
    tenant_id: str,
    actor: str,
    now: datetime | None = None,
) -> AutomationRunResult:
    """Einen Automation-Lauf ausführen: Regeln, dann deterministische Action-Generierung."""
    ts = _aware(now or datetime.now(UTC))
    run_id = str(uuid4())
    res = AutomationRunResult(run_id=run_id, rule_keys=[])

    session.add(
        RemediationAutomationRunTable(
            id=run_id,
            tenant_id=tenant_id,
            started_at_utc=ts,
            finished_at_utc=None,
            summary_json=None,
        )
    )

    actions = (
        await session.scalars(
            select(RemediationActionTable).where(
                RemediationActionTable.tenant_id == tenant_id,
                RemediationActionTable.status.in_(ACTIVE),
            )
        )
    ).all()

    for row in actions:
        due = row.due_at_utc
        st = row.status
        if not _is_overdue_work_item(st, due, ts):
            continue
        assert due is not None
        if not await _open_escalation_exists(session, tenant_id, row.id, REASON_OVERDUE):
            eid = str(uuid4())
            session.add(
                RemediationEscalationTable(
                    id=eid,
                    tenant_id=tenant_id,
                    action_id=row.id,
                    run_id=run_id,
                    severity="overdue",
                    reason_code=REASON_OVERDUE,
                    detail="Fälligkeit überschritten; Maßnahme nicht abgeschlossen.",
                    status="open",
                    created_at_utc=ts,
                )
            )
            await _write_event(
                session,
                tenant_id,
                run_id,
                EVENT_ESCALATION,
                row.id,
                {"escalation_id": eid, "severity": "overdue", "reason": REASON_OVERDUE},
            )
            res.escalations_created += 1
            res.events_written += 1
            if REASON_OVERDUE not in res.rule_keys:
                res.rule_keys.append(REASON_OVERDUE)

        if row.priority == "critical" and (ts - _aware(due)) > timedelta(days=7):
            if not await _open_escalation_exists(session, tenant_id, row.id, REASON_SEVERE):
                eid = str(uuid4())
                session.add(
                    RemediationEscalationTable(
                        id=eid,
                        tenant_id=tenant_id,
                        action_id=row.id,
                        run_id=run_id,
                        severity="severe",
                        reason_code=REASON_SEVERE,
                        detail="Kritische Priorität und >7 Tage überfällig.",
                        status="open",
                        created_at_utc=ts,
                    )
                )
                await _write_event(
                    session,
                    tenant_id,
                    run_id,
                    EVENT_ESCALATION,
                    row.id,
                    {"escalation_id": eid, "severity": "severe", "reason": REASON_SEVERE},
                )
                res.escalations_created += 1
                res.events_written += 1
                if REASON_SEVERE not in res.rule_keys:
                    res.rule_keys.append(REASON_SEVERE)

    br_rows = (
        await session.execute(
            select(BoardReportActionTable, BoardReportTable.period_end)
            .join(BoardReportTable, BoardReportTable.id == BoardReportActionTable.report_id)
            .where(
                BoardReportActionTable.tenant_id == tenant_id,
                BoardReportActionTable.status == "open",
                BoardReportTable.period_end < ts,
            )
        )
    ).all()
    for ba, _period_end in br_rows:
        aid = await session.scalar(
            select(RemediationActionLinkTable.action_id)
            .where(
                RemediationActionLinkTable.tenant_id == tenant_id,
                RemediationActionLinkTable.entity_type == ENTITY_BOARD_REPORT_ACTION,
                RemediationActionLinkTable.entity_id == ba.id,
            )
            .limit(1)
        )
        if aid is None:
            continue
        arow = await session.get(RemediationActionTable, aid)
        if arow is None or arow.tenant_id != tenant_id or arow.status not in ACTIVE:
            continue
        if await _open_escalation_exists(session, tenant_id, aid, REASON_BOARD_PERIOD):
            continue
        eid = str(uuid4())
        session.add(
            RemediationEscalationTable(
                id=eid,
                tenant_id=tenant_id,
                action_id=aid,
                run_id=run_id,
                severity="management_followup",
                reason_code=REASON_BOARD_PERIOD,
                detail="Board-Action offen nach Ende der Berichtsperiode.",
                status="open",
                created_at_utc=ts,
            )
        )
        await _write_event(
            session,
            tenant_id,
            run_id,
            EVENT_ESCALATION,
            aid,
            {
                "escalation_id": eid,
                "severity": "management_followup",
                "board_report_action_id": ba.id,
            },
        )
        res.escalations_created += 1
        res.events_written += 1
        if REASON_BOARD_PERIOD not in res.rule_keys:
            res.rule_keys.append(REASON_BOARD_PERIOD)

    ev_gaps: list[dict[str, str]] = []
    ev_stmt = (
        select(
            GovernanceControlTable.id,
            GovernanceControlTable.title,
            GovernanceControlTable.status,
        )
        .where(
            GovernanceControlTable.tenant_id == tenant_id,
            GovernanceControlTable.status == "implemented",
            ~GovernanceControlTable.id.in_(
                select(GovernanceControlEvidenceTable.control_id).where(
                    GovernanceControlEvidenceTable.tenant_id == tenant_id
                )
            ),
        )
        .limit(20)
    )
    for cid, title, st in (await session.execute(ev_stmt)).all():
        ev_gaps.append(
            {
                "control_id": str(cid),
                "title": title,
                "status": str(st),
            }
        )
    if ev_gaps:
        if REASON_EVIDENCE not in res.rule_keys:
            res.rule_keys.append(REASON_EVIDENCE)
        await _write_event(
            session,
            tenant_id,
            run_id,
            EVENT_RECOMMENDATION,
            None,
            {
                "kind": REASON_EVIDENCE,
                "message": "Evidence binnen 14 Tagen für priorisierte Controls nachreichen.",
                "gaps": ev_gaps,
            },
        )
        res.events_written += 1

    # Reminder: bevorstehende Fälligkeit (nächste 7 Tage) — eine Zeile pro Maßnahme
    day_end = ts + timedelta(days=7)
    for row in actions:
        if row.due_at_utc is None:
            continue
        due = _aware(row.due_at_utc)
        if ts <= due <= day_end:
            await session.execute(
                delete(RemediationReminderTable).where(
                    RemediationReminderTable.tenant_id == tenant_id,
                    RemediationReminderTable.action_id == row.id,
                )
            )
            rid = str(uuid4())
            session.add(
                RemediationReminderTable(
                    id=rid,
                    tenant_id=tenant_id,
                    action_id=row.id,
                    run_id=run_id,
                    kind="due_window",
                    remind_at_utc=due,
                    status="open",
                    created_at_utc=ts,
                )
            )
            await _write_event(
                session,
                tenant_id,
                run_id,
                EVENT_REMINDER,
                row.id,
                {"reminder_id": rid, "remind_at_utc": due.isoformat()},
            )
            res.reminders_upserted += 1
            res.events_written += 1
            if "due_window_reminder" not in res.rule_keys:
                res.rule_keys.append("due_window_reminder")

    for inc in (
        await session.scalars(
            select(ServiceHealthIncidentTable).where(
                ServiceHealthIncidentTable.tenant_id == tenant_id,
                ServiceHealthIncidentTable.incident_state == "open",
                ServiceHealthIncidentTable.severity == "critical",
            )
        )
    ).all():
        nlink = await session.scalar(
            select(func.count())
            .select_from(RemediationActionLinkTable)
            .where(
                RemediationActionLinkTable.tenant_id == tenant_id,
                RemediationActionLinkTable.entity_type == "service_health_incident",
                RemediationActionLinkTable.entity_id == inc.id,
            )
        )
        if nlink and int(nlink) > 0:
            continue
        await _write_event(
            session,
            tenant_id,
            run_id,
            EVENT_RECOMMENDATION,
            None,
            {
                "incident_id": inc.id,
                "title": inc.title,
                "hint": (
                    "Kritisches Incident ohne verknüpfte Remediation-Maßnahme; "
                    "Generierung vorschlagen."
                ),
            },
        )
        res.events_written += 1
        if REASON_INCIDENT not in res.rule_keys:
            res.rule_keys.append(REASON_INCIDENT)

    gen_n, gkeys = await generate_remediation_actions(
        session, tenant_id=tenant_id, actor=actor, now=ts
    )
    res.generated_actions = gen_n
    for k in gkeys:
        if k not in res.rule_keys:
            res.rule_keys.append(k)

    run_row = await session.get(RemediationAutomationRunTable, run_id)
    if run_row is not None:
        run_row.finished_at_utc = datetime.now(UTC)
        run_row.escalations_created = res.escalations_created
        run_row.reminders_upserted = res.reminders_upserted
        run_row.events_written = res.events_written
        run_row.generated_actions_count = res.generated_actions
        run_row.summary_json = json.dumps(
            {
                "rule_keys": res.rule_keys,
                "escalations_created": res.escalations_created,
                "reminders_upserted": res.reminders_upserted,
                "events_written": res.events_written,
                "generated_actions": res.generated_actions,
            },
            ensure_ascii=False,
        )
    return res
