"""Remediation Automation & Escalation — regelbasiert, mandantenisoliert, auditierbar."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import get_api_key_and_tenant
from app.db_tenant import get_async_db
from app.governance_taxonomy import GovernanceAuditAction, GovernanceAuditEntity
from app.models_db import (
    AuditLogTable,
    RemediationAutomationRunTable,
    RemediationEscalationTable,
    RemediationReminderTable,
)
from app.remediation_automation_models import (
    AcknowledgeEscalationResponse,
    RemediationAutomationRunResponse,
    RemediationAutomationSummary,
    RemediationEscalationListItem,
    RemediationEscalationListResponse,
    RemediationReminderListItem,
    RemediationReminderListResponse,
)
from app.services.remediation_actions_service import tenant_summary_counts
from app.services.remediation_automation_service import run_remediation_automation

router = APIRouter(
    prefix="/api/v1/governance/remediation-actions",
    tags=["governance", "remediation-automation"],
)


def _actor(request: Request) -> str:
    return request.headers.get("x-actor-id", "api:remediation-automation")


async def _audit(
    session: AsyncSession,
    tenant_id: str,
    actor: str,
    action: str,
    entity_id: str,
    payload: dict[str, object],
) -> None:
    session.add(
        AuditLogTable(
            tenant_id=tenant_id,
            actor=actor,
            action=action,
            entity_type=GovernanceAuditEntity.REMEDIATION_ACTION.value,
            entity_id=entity_id,
            after=json.dumps(payload, ensure_ascii=False, default=str),
            outcome="success",
            actor_role="compliance_officer",
            created_at_utc=datetime.now(UTC),
        )
    )


@router.get("/automation/summary", response_model=RemediationAutomationSummary)
async def get_automation_summary(
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> RemediationAutomationSummary:
    now = datetime.now(UTC)
    s = await tenant_summary_counts(session, tenant_id, now=now)
    severe = int(
        (
            await session.scalar(
                select(func.count())
                .select_from(RemediationEscalationTable)
                .where(
                    RemediationEscalationTable.tenant_id == tenant_id,
                    RemediationEscalationTable.status == "open",
                    RemediationEscalationTable.severity == "severe",
                )
            )
        )
        or 0
    )
    mgmt = int(
        (
            await session.scalar(
                select(func.count())
                .select_from(RemediationEscalationTable)
                .where(
                    RemediationEscalationTable.tenant_id == tenant_id,
                    RemediationEscalationTable.status == "open",
                    RemediationEscalationTable.severity == "management_followup",
                )
            )
        )
        or 0
    )
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_day = start_day + timedelta(days=1)
    rem_today = int(
        (
            await session.scalar(
                select(func.count())
                .select_from(RemediationReminderTable)
                .where(
                    RemediationReminderTable.tenant_id == tenant_id,
                    RemediationReminderTable.status == "open",
                    RemediationReminderTable.remind_at_utc >= start_day,
                    RemediationReminderTable.remind_at_utc < end_day,
                )
            )
        )
        or 0
    )
    week_ago = now - timedelta(days=7)
    sum_q = select(
        func.coalesce(func.sum(RemediationAutomationRunTable.generated_actions_count), 0)
    ).where(
        RemediationAutomationRunTable.tenant_id == tenant_id,
        RemediationAutomationRunTable.started_at_utc >= week_ago,
    )
    auto_sum = int((await session.scalar(sum_q)) or 0)
    return RemediationAutomationSummary(
        overdue_actions=s["overdue_actions"],
        severe_escalations_open=severe,
        management_escalations_open=mgmt,
        reminders_due_today=rem_today,
        auto_generated_actions_7d=auto_sum,
    )


@router.post("/automation/run", response_model=RemediationAutomationRunResponse)
async def post_automation_run(
    request: Request,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> RemediationAutomationRunResponse:
    actor = _actor(request)
    res = await run_remediation_automation(session, tenant_id=tenant_id, actor=actor)
    await _audit(
        session,
        tenant_id,
        actor,
        GovernanceAuditAction.REMEDIATION_AUTOMATION_RUN.value,
        res.run_id,
        {
            "escalations": res.escalations_created,
            "reminders": res.reminders_upserted,
            "events": res.events_written,
            "generated": res.generated_actions,
        },
    )
    await session.commit()
    return RemediationAutomationRunResponse(
        run_id=res.run_id,
        escalations_created=res.escalations_created,
        reminders_upserted=res.reminders_upserted,
        events_written=res.events_written,
        generated_actions=res.generated_actions,
        rule_keys=res.rule_keys,
    )


@router.get("/escalations", response_model=RemediationEscalationListResponse)
async def list_escalations(
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
    status_filter: str | None = Query(None, alias="status"),
    severity: str | None = None,
    limit: int = Query(200, ge=1, le=500),
) -> RemediationEscalationListResponse:
    stmt = select(RemediationEscalationTable).where(
        RemediationEscalationTable.tenant_id == tenant_id
    )
    if status_filter:
        stmt = stmt.where(RemediationEscalationTable.status == status_filter)
    if severity:
        stmt = stmt.where(RemediationEscalationTable.severity == severity)
    stmt = stmt.order_by(RemediationEscalationTable.created_at_utc.desc()).limit(limit)
    rows = (await session.scalars(stmt)).all()
    return RemediationEscalationListResponse(
        items=[
            RemediationEscalationListItem(
                id=r.id,
                action_id=r.action_id,
                severity=r.severity,
                reason_code=r.reason_code,
                detail=r.detail,
                status=r.status,
                created_at_utc=r.created_at_utc,
                run_id=r.run_id,
            )
            for r in rows
        ],
    )


@router.get("/reminders", response_model=RemediationReminderListResponse)
async def list_reminders(
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(200, ge=1, le=500),
) -> RemediationReminderListResponse:
    stmt = select(RemediationReminderTable).where(RemediationReminderTable.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(RemediationReminderTable.status == status_filter)
    stmt = stmt.order_by(RemediationReminderTable.remind_at_utc.asc()).limit(limit)
    rows = (await session.scalars(stmt)).all()
    return RemediationReminderListResponse(
        items=[
            RemediationReminderListItem(
                id=r.id,
                action_id=r.action_id,
                kind=r.kind,
                remind_at_utc=r.remind_at_utc,
                status=r.status,
                created_at_utc=r.created_at_utc,
                run_id=r.run_id,
            )
            for r in rows
        ],
    )


@router.post(
    "/{action_id}/acknowledge-escalation",
    response_model=AcknowledgeEscalationResponse,
    status_code=status.HTTP_200_OK,
)
async def acknowledge_escalation_for_action(
    action_id: str,
    request: Request,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> AcknowledgeEscalationResponse:
    """Alle offenen Eskalationen zu einer Maßnahme quittieren."""
    actor = _actor(request)
    rows = (
        await session.scalars(
            select(RemediationEscalationTable)
            .where(
                RemediationEscalationTable.tenant_id == tenant_id,
                RemediationEscalationTable.action_id == action_id,
                RemediationEscalationTable.status == "open",
            )
        )
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail="No open escalations for this action.")
    now = datetime.now(UTC)
    ids: list[str] = []
    for r in rows:
        r.status = "acknowledged"
        r.acknowledged_at_utc = now
        r.acknowledged_by = actor
        ids.append(r.id)
    await _audit(
        session,
        tenant_id,
        actor,
        GovernanceAuditAction.REMEDIATION_ESCALATION_ACK.value,
        action_id,
        {"acknowledged_ids": ids},
    )
    await session.commit()
    return AcknowledgeEscalationResponse(acknowledged=len(ids), escalation_ids=ids)
