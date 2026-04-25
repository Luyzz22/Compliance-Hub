"""Governance Workflow Orchestration — mandanten-isoliert, AsyncSession, Audit-Log."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import get_api_key_and_tenant
from app.db_tenant import get_async_db
from app.governance_taxonomy import GovernanceAuditAction, GovernanceAuditEntity
from app.governance_workflow_models import (
    GovernanceNotificationDeliveryRead,
    GovernanceNotificationRead,
    GovernanceNotificationTestRequest,
    GovernanceNotificationTestResponse,
    GovernanceWorkflowDashboardRead,
    GovernanceWorkflowEventRead,
    GovernanceWorkflowKpisRead,
    GovernanceWorkflowRunRead,
    GovernanceWorkflowRunRequest,
    GovernanceWorkflowRunResponse,
    GovernanceWorkflowTaskDetailRead,
    GovernanceWorkflowTaskHistoryRead,
    GovernanceWorkflowTaskListItemRead,
    GovernanceWorkflowTaskUpdate,
    GovernanceWorkflowTemplateRead,
)
from app.models_db import AuditLogTable, GovernanceWorkflowTaskTable
from app.services import governance_workflow_service as gws
from app.services.governance_workflow_service import _task_is_overdue

router = APIRouter(
    prefix="/api/v1/governance/workflows",
    tags=["governance", "workflows"],
)


def _actor(request: Request) -> str:
    return request.headers.get("x-actor-id", "api:governance-workflows")


async def _audit(
    session: AsyncSession,
    *,
    tenant_id: str,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
) -> None:
    now = datetime.now(UTC)
    session.add(
        AuditLogTable(
            tenant_id=tenant_id,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            after=json.dumps(payload, default=str),
            outcome="success",
            actor_role="compliance_officer",
            created_at_utc=now,
        )
    )


def _task_to_list_item(
    r: GovernanceWorkflowTaskTable, *, now: datetime
) -> GovernanceWorkflowTaskListItemRead:
    tags = r.framework_tags_json or []
    if not isinstance(tags, list):
        tags = []
    return GovernanceWorkflowTaskListItemRead(
        id=r.id,
        title=r.title,
        status=r.status,
        priority=r.priority,
        source_type=r.source_type,
        source_id=r.source_id,
        assignee_user_id=r.assignee_user_id,
        due_at_utc=r.due_at_utc,
        template_code=r.template_code,
        framework_tags=[str(x) for x in tags],
        escalation_level=r.escalation_level,
        created_at_utc=r.created_at_utc,
        updated_at_utc=r.updated_at_utc,
        is_overdue=_task_is_overdue(status=r.status, due_at_utc=r.due_at_utc, now=now),
    )


@router.get("", response_model=GovernanceWorkflowDashboardRead)
async def get_workflow_dashboard(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: AsyncSession = Depends(get_async_db),
) -> GovernanceWorkflowDashboardRead:
    k = await gws.compute_kpis(session, tenant_id)
    runs = await gws.list_runs(session, tenant_id, limit=20)
    tpls = await gws.list_template_rows(session)
    return GovernanceWorkflowDashboardRead(
        kpis=GovernanceWorkflowKpisRead(**k),
        rule_bundle_version=gws.RULE_BUNDLE_VERSION,
        recent_runs=[
            GovernanceWorkflowRunRead(
                id=r.id,
                tenant_id=r.tenant_id,
                trigger_mode=r.trigger_mode,
                status=r.status,
                rule_bundle_version=r.rule_bundle_version,
                summary=r.summary_json,
                started_at_utc=r.started_at_utc,
                completed_at_utc=r.completed_at_utc,
            )
            for r in runs
        ],
        templates=[
            GovernanceWorkflowTemplateRead(
                id=t.id,
                code=t.code,
                title=t.title,
                description=t.description,
                default_sla_days=t.default_sla_days,
                is_system=t.is_system,
            )
            for t in tpls
        ],
    )


@router.post(
    "/run",
    response_model=GovernanceWorkflowRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_workflow_run(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    request: Request,
    session: AsyncSession = Depends(get_async_db),
    body: GovernanceWorkflowRunRequest | None = None,
) -> GovernanceWorkflowRunResponse:
    actor = _actor(request)
    profile = body.rule_profile if body is not None else "default"
    try:
        out = await gws.run_deterministic_sync(session, tenant_id, profile)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    await _audit(
        session,
        tenant_id=tenant_id,
        actor=actor,
        action=GovernanceAuditAction.GOVERNANCE_WORKFLOW_RUN_SYNC.value,
        entity_type=GovernanceAuditEntity.GOVERNANCE_WORKFLOW_RUN.value,
        entity_id=str(out["run_id"]),
        payload={**{k: v for k, v in out.items()}, "actor": actor},
    )
    await session.commit()
    return GovernanceWorkflowRunResponse(
        run_id=str(out["run_id"]),
        status=str(out["status"]),
        tasks_materialized=int(out["tasks_materialized"]),
        events_written=int(out["events_written"]),
        notifications_queued=int(out["notifications_queued"]),
        rule_bundle_version=str(out["rule_bundle_version"]),
    )


@router.get("/tasks", response_model=list[GovernanceWorkflowTaskListItemRead])
async def list_workflow_tasks(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: AsyncSession = Depends(get_async_db),
    status_filter: str | None = Query(None, alias="status"),
    source_type: str | None = Query(None),
    assignee: str | None = Query(None),
    severity: str | None = Query(
        None,
        description="Alias für task.priority in diesem MVP (critical|high|medium|low).",
    ),
    framework: str | None = Query(
        None,
        description="Teilstring in framework_tags (MVP, LIKE).",
    ),
    limit: int = Query(200, ge=1, le=500),
) -> list[GovernanceWorkflowTaskListItemRead]:
    now = datetime.now(UTC)
    rows = await gws.list_tasks_for_tenant(
        session,
        tenant_id,
        status=status_filter,
        source_type=source_type,
        assignee=assignee,
        framework_tag=framework,
        priority=severity,
        limit=limit,
    )
    return [_task_to_list_item(r, now=now) for r in rows]


@router.get("/tasks/{task_id}", response_model=GovernanceWorkflowTaskDetailRead)
async def get_workflow_task_detail(
    task_id: str,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: AsyncSession = Depends(get_async_db),
) -> GovernanceWorkflowTaskDetailRead:
    t = await gws.get_task(session, tenant_id, task_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    now = datetime.now(UTC)
    tags = t.framework_tags_json or []
    if not isinstance(tags, list):
        tags = []
    hist = await gws.list_task_history(session, tenant_id, task_id)
    return GovernanceWorkflowTaskDetailRead(
        id=t.id,
        tenant_id=t.tenant_id,
        title=t.title,
        description=t.description,
        status=t.status,
        priority=t.priority,
        source_type=t.source_type,
        source_id=t.source_id,
        source_ref=t.source_ref_json or {},
        assignee_user_id=t.assignee_user_id,
        due_at_utc=t.due_at_utc,
        template_code=t.template_code,
        framework_tags=[str(x) for x in tags],
        last_comment=t.last_comment,
        run_id=t.run_id,
        created_at_utc=t.created_at_utc,
        updated_at_utc=t.updated_at_utc,
        is_overdue=_task_is_overdue(status=t.status, due_at_utc=t.due_at_utc, now=now),
        history=[
            GovernanceWorkflowTaskHistoryRead(
                at_utc=h.at_utc,
                from_status=h.from_status,
                to_status=h.to_status,
                actor_id=h.actor_id,
                note=h.note,
                payload_json=h.payload_json,
            )
            for h in hist
        ],
    )


@router.patch("/tasks/{task_id}", response_model=GovernanceWorkflowTaskListItemRead)
async def patch_workflow_task(
    task_id: str,
    body: GovernanceWorkflowTaskUpdate,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    request: Request,
    session: AsyncSession = Depends(get_async_db),
) -> GovernanceWorkflowTaskListItemRead:
    actor = _actor(request)
    try:
        t = await gws.update_workflow_task(
            session,
            tenant_id,
            task_id,
            status=body.status,
            assignee_user_id=body.assignee_user_id,
            last_comment=body.last_comment,
            actor_id=actor,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        ) from None
    await _audit(
        session,
        tenant_id=tenant_id,
        actor=actor,
        action=GovernanceAuditAction.GOVERNANCE_WORKFLOW_TASK_UPDATE.value,
        entity_type=GovernanceAuditEntity.GOVERNANCE_WORKFLOW_TASK.value,
        entity_id=task_id,
        payload=body.model_dump(),
    )
    await session.commit()
    now = datetime.now(UTC)
    return _task_to_list_item(t, now=now)


@router.get("/events", response_model=list[GovernanceWorkflowEventRead])
async def list_workflow_events(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: AsyncSession = Depends(get_async_db),
    limit: int = Query(100, ge=1, le=500),
) -> list[GovernanceWorkflowEventRead]:
    rows = await gws.list_events(session, tenant_id, limit=limit)
    return [
        GovernanceWorkflowEventRead(
            id=e.id,
            at_utc=e.at_utc,
            event_type=e.event_type,
            severity=e.severity,
            ref_task_id=e.ref_task_id,
            source_type=e.source_type,
            source_id=e.source_id,
            message=e.message,
            payload_json=e.payload_json,
        )
        for e in rows
    ]


@router.get(
    "/notifications",
    response_model=list[GovernanceNotificationRead],
)
async def list_governance_notifications(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: AsyncSession = Depends(get_async_db),
    limit: int = Query(100, ge=1, le=500),
) -> list[GovernanceNotificationRead]:
    rows = await gws.list_notifications(session, tenant_id, limit=limit)
    return [
        GovernanceNotificationRead(
            id=n.id,
            ref_task_id=n.ref_task_id,
            channel=n.channel,
            status=n.status,
            title=n.title,
            body_text=n.body_text,
            created_at_utc=n.created_at_utc,
        )
        for n in rows
    ]


@router.get(
    "/notification-deliveries",
    response_model=list[GovernanceNotificationDeliveryRead],
)
async def list_governance_notification_deliveries(
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    session: AsyncSession = Depends(get_async_db),
    limit: int = Query(100, ge=1, le=500),
) -> list[GovernanceNotificationDeliveryRead]:
    rows = await gws.list_notification_deliveries(session, tenant_id, limit=limit)
    return [
        GovernanceNotificationDeliveryRead(
            id=d.id,
            notification_id=d.notification_id,
            channel=d.channel,
            result=d.result,
            detail=d.detail,
            delivered_at_utc=d.delivered_at_utc,
        )
        for d in rows
    ]


@router.post(
    "/notifications/test",
    response_model=GovernanceNotificationTestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_test_notification(
    body: GovernanceNotificationTestRequest,
    tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
    request: Request,
    session: AsyncSession = Depends(get_async_db),
) -> GovernanceNotificationTestResponse:
    actor = _actor(request)
    try:
        n_id, d_id = await gws.create_test_notification(
            session,
            tenant_id,
            channel=body.channel,
            title=body.title,
            body=body.body,
            ref_task_id=body.ref_task_id,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced task not found",
        ) from e
    await _audit(
        session,
        tenant_id=tenant_id,
        actor=actor,
        action=GovernanceAuditAction.GOVERNANCE_WORKFLOW_NOTIFICATION_TEST.value,
        entity_type=GovernanceAuditEntity.GOVERNANCE_WORKFLOW_NOTIFICATION.value,
        entity_id=n_id,
        payload={"channel": body.channel, "title": body.title, "ref_task_id": body.ref_task_id},
    )
    await session.commit()
    return GovernanceNotificationTestResponse(notification_id=n_id, delivery_id=d_id, result="ok")
