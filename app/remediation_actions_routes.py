"""Remediation & Action Tracking APIs — nachvollziehbare Regeln, Mandanten-Firewall, Audit Trail."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, case, desc, nulls_last, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import get_api_key_and_tenant
from app.db_tenant import get_async_db
from app.governance_taxonomy import GovernanceAuditAction, GovernanceAuditEntity
from app.models_db import (
    AuditLogTable,
    GovernanceAuditCaseTable,
    GovernanceControlTable,
    RemediationActionLinkTable,
    RemediationActionTable,
    RemediationCommentTable,
    RemediationStatusHistoryTable,
)
from app.remediation_actions_models import (
    RemediationActionCreate,
    RemediationActionDetailRead,
    RemediationActionListItemRead,
    RemediationActionListResponse,
    RemediationActionUpdate,
    RemediationCommentCreate,
    RemediationCommentRead,
    RemediationGenerateResponse,
    RemediationLinkRead,
    RemediationStatusHistoryRead,
    RemediationSummaryRead,
)
from app.services.remediation_actions_service import (
    ENTITY_GOVERNANCE_AUDIT_CASE,
    ENTITY_GOVERNANCE_CONTROL,
    generate_remediation_actions,
    tenant_summary_counts,
)

router = APIRouter(
    prefix="/api/v1/governance/remediation-actions",
    tags=["governance", "remediation-actions"],
)


async def _audit_event(
    session: AsyncSession,
    *,
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
            after=json.dumps(payload),
            outcome="success",
            actor_role="compliance_officer",
            created_at_utc=datetime.now(UTC),
        )
    )


def _actor(request: Request) -> str:
    return request.headers.get("x-actor-id", "api:governance-remediation")


def _remediation_is_overdue(*, status: str, due_at_utc: datetime | None, now: datetime) -> bool:
    if due_at_utc is None or status not in ("open", "in_progress", "blocked"):
        return False
    return due_at_utc < now


def _ilike_search_term(raw: str) -> str:
    t = raw.strip()
    return t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _load_links(
    session: AsyncSession, tenant_id: str, action_ids: list[str]
) -> dict[str, list]:
    if not action_ids:
        return {}
    rows = (
        await session.scalars(
            select(RemediationActionLinkTable).where(
                RemediationActionLinkTable.tenant_id == tenant_id,
                RemediationActionLinkTable.action_id.in_(action_ids),
            )
        )
    ).all()
    out: dict[str, list] = {}
    for r in rows:
        out.setdefault(r.action_id, []).append(r)
    return out


@router.get("", response_model=RemediationActionListResponse)
async def list_remediation_actions(
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = None,
    category: str | None = Query(
        None, description="manual | audit | control | incident | board | ai_act | nis2"
    ),
    rule_key: str | None = None,
    framework_tag: str | None = Query(
        None, description="Filter über verknüpfte Controls, z. B. EU_AI_ACT"
    ),
    search: str | None = Query(
        None,
        max_length=200,
        description="Teilstring-Suche im Titel (mandanten-isoliert, LIKE mit Escape).",
    ),
    sort: str = Query(
        "updated_desc",
        pattern="^(updated_desc|due_asc|due_desc|priority_desc)$",
        description="Sortierung der Liste",
    ),
    limit: int = Query(200, ge=1, le=500),
) -> RemediationActionListResponse:
    now = datetime.now(UTC)
    summary_raw = await tenant_summary_counts(session, tenant_id, now=now)
    stmt = select(RemediationActionTable).where(RemediationActionTable.tenant_id == tenant_id)
    if status_filter:
        stmt = stmt.where(RemediationActionTable.status == status_filter)
    if priority:
        stmt = stmt.where(RemediationActionTable.priority == priority)
    if category:
        stmt = stmt.where(RemediationActionTable.category == category)
    if rule_key:
        stmt = stmt.where(RemediationActionTable.rule_key == rule_key)
    if search and search.strip():
        term = _ilike_search_term(search)
        if term:
            stmt = stmt.where(RemediationActionTable.title.ilike(f"%{term}%", escape="\\"))
    if framework_tag:
        subq = (
            select(RemediationActionLinkTable.action_id)
            .where(
                RemediationActionLinkTable.tenant_id == tenant_id,
                RemediationActionLinkTable.entity_type == ENTITY_GOVERNANCE_CONTROL,
                RemediationActionLinkTable.entity_id.in_(
                    select(GovernanceControlTable.id).where(
                        GovernanceControlTable.tenant_id == tenant_id,
                        GovernanceControlTable.framework_tags_json.like(f"%{framework_tag}%"),
                    )
                ),
            )
            .distinct()
        )
        stmt = stmt.where(RemediationActionTable.id.in_(subq))
    prio_rank = case(
        (RemediationActionTable.priority == "critical", 4),
        (RemediationActionTable.priority == "high", 3),
        (RemediationActionTable.priority == "medium", 2),
        else_=1,
    )
    if sort == "due_asc":
        stmt = stmt.order_by(
            nulls_last(asc(RemediationActionTable.due_at_utc)),
            desc(RemediationActionTable.updated_at_utc),
        )
    elif sort == "due_desc":
        stmt = stmt.order_by(
            nulls_last(desc(RemediationActionTable.due_at_utc)),
            desc(RemediationActionTable.updated_at_utc),
        )
    elif sort == "priority_desc":
        stmt = stmt.order_by(
            desc(prio_rank),
            desc(RemediationActionTable.updated_at_utc),
        )
    else:
        stmt = stmt.order_by(desc(RemediationActionTable.updated_at_utc))
    stmt = stmt.limit(limit)
    rows = (await session.scalars(stmt)).all()
    ids = [r.id for r in rows]
    link_map = await _load_links(session, tenant_id, ids)
    items: list[RemediationActionListItemRead] = []
    for r in rows:
        lk = link_map.get(r.id, [])
        items.append(
            RemediationActionListItemRead(
                id=r.id,
                title=r.title,
                status=r.status,
                priority=r.priority,
                owner=r.owner,
                due_at_utc=r.due_at_utc,
                is_overdue=_remediation_is_overdue(
                    status=r.status, due_at_utc=r.due_at_utc, now=now
                ),
                category=r.category,
                rule_key=r.rule_key,
                updated_at_utc=r.updated_at_utc,
                links=[
                    RemediationLinkRead(entity_type=x.entity_type, entity_id=x.entity_id)
                    for x in lk
                ],
            )
        )
    return RemediationActionListResponse(
        items=items,
        summary=RemediationSummaryRead(
            open_actions=summary_raw["open_actions"],
            backlog_actions=summary_raw["backlog_actions"],
            overdue_actions=summary_raw["overdue_actions"],
            blocked_actions=summary_raw["blocked_actions"],
            due_this_week=summary_raw["due_this_week"],
        ),
    )


@router.post("", response_model=RemediationActionDetailRead, status_code=status.HTTP_201_CREATED)
async def create_remediation_action(
    body: RemediationActionCreate,
    request: Request,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> RemediationActionDetailRead:
    actor = _actor(request)
    aid = str(uuid4())
    now = datetime.now(UTC)
    for link in body.links:
        if link.entity_type == ENTITY_GOVERNANCE_CONTROL:
            ctl = await session.get(GovernanceControlTable, link.entity_id)
            if ctl is None or ctl.tenant_id != tenant_id:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid governance_control link for this tenant.",
                )
        elif link.entity_type == ENTITY_GOVERNANCE_AUDIT_CASE:
            ac = await session.get(GovernanceAuditCaseTable, link.entity_id)
            if ac is None or ac.tenant_id != tenant_id:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid governance_audit_case link for this tenant.",
                )

    session.add(
        RemediationActionTable(
            id=aid,
            tenant_id=tenant_id,
            title=body.title,
            description=body.description,
            status="open",
            priority=body.priority,
            owner=body.owner,
            due_at_utc=body.due_at_utc,
            category=body.category,
            rule_key=None,
            dedupe_key=None,
            deferred_note=None,
            created_at_utc=now,
            updated_at_utc=now,
            created_by=actor,
        )
    )
    for link in body.links:
        session.add(
            RemediationActionLinkTable(
                id=str(uuid4()),
                tenant_id=tenant_id,
                action_id=aid,
                entity_type=link.entity_type,
                entity_id=link.entity_id,
            )
        )
    session.add(
        RemediationStatusHistoryTable(
            id=str(uuid4()),
            tenant_id=tenant_id,
            action_id=aid,
            from_status=None,
            to_status="open",
            changed_at_utc=now,
            changed_by=actor,
            note="Erstellt",
        )
    )
    await _audit_event(
        session,
        tenant_id=tenant_id,
        actor=actor,
        action=GovernanceAuditAction.REMEDIATION_ACTION_CREATE.value,
        entity_id=aid,
        payload={"title": body.title, "category": body.category},
    )
    await session.commit()
    res = await get_remediation_action(aid, tenant_id, session)
    return res


@router.post("/generate", response_model=RemediationGenerateResponse)
async def generate_remediation_actions_endpoint(
    request: Request,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> RemediationGenerateResponse:
    actor = _actor(request)
    evaluated_at = datetime.now(UTC)
    n, touched = await generate_remediation_actions(
        session, tenant_id=tenant_id, actor=actor, now=evaluated_at
    )
    await _audit_event(
        session,
        tenant_id=tenant_id,
        actor=actor,
        action=GovernanceAuditAction.REMEDIATION_ACTION_GENERATE.value,
        entity_id=tenant_id,
        payload={
            "created_count": n,
            "rule_keys": touched,
            "evaluated_at_utc": evaluated_at.isoformat(),
        },
    )
    await session.commit()
    return RemediationGenerateResponse(
        created_count=n,
        rule_keys_touched=touched,
        evaluated_at_utc=evaluated_at,
    )


@router.get("/{action_id}", response_model=RemediationActionDetailRead)
async def get_remediation_action(
    action_id: str,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> RemediationActionDetailRead:
    now = datetime.now(UTC)
    row = await session.get(RemediationActionTable, action_id)
    if row is None or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Remediation action not found.")
    links = (
        await session.scalars(
            select(RemediationActionLinkTable).where(
                RemediationActionLinkTable.tenant_id == tenant_id,
                RemediationActionLinkTable.action_id == action_id,
            )
        )
    ).all()
    comments = (
        await session.scalars(
            select(RemediationCommentTable)
            .where(
                RemediationCommentTable.tenant_id == tenant_id,
                RemediationCommentTable.action_id == action_id,
            )
            .order_by(RemediationCommentTable.created_at_utc)
        )
    ).all()
    hist = (
        await session.scalars(
            select(RemediationStatusHistoryTable)
            .where(
                RemediationStatusHistoryTable.tenant_id == tenant_id,
                RemediationStatusHistoryTable.action_id == action_id,
            )
            .order_by(RemediationStatusHistoryTable.changed_at_utc)
        )
    ).all()
    return RemediationActionDetailRead(
        id=row.id,
        tenant_id=row.tenant_id,
        title=row.title,
        description=row.description,
        status=row.status,
        priority=row.priority,
        owner=row.owner,
        due_at_utc=row.due_at_utc,
        is_overdue=_remediation_is_overdue(
            status=row.status, due_at_utc=row.due_at_utc, now=now
        ),
        category=row.category,
        rule_key=row.rule_key,
        deferred_note=row.deferred_note,
        created_at_utc=row.created_at_utc,
        updated_at_utc=row.updated_at_utc,
        created_by=row.created_by,
        links=[
            RemediationLinkRead(entity_type=x.entity_type, entity_id=x.entity_id) for x in links
        ],
        comments=[
            RemediationCommentRead(
                id=c.id,
                body=c.body,
                created_by=c.created_by,
                created_at_utc=c.created_at_utc,
            )
            for c in comments
        ],
        status_history=[
            RemediationStatusHistoryRead(
                id=h.id,
                from_status=h.from_status,
                to_status=h.to_status,
                changed_at_utc=h.changed_at_utc,
                changed_by=h.changed_by,
                note=h.note,
            )
            for h in hist
        ],
    )


@router.patch("/{action_id}", response_model=RemediationActionDetailRead)
async def patch_remediation_action(
    action_id: str,
    body: RemediationActionUpdate,
    request: Request,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> RemediationActionDetailRead:
    actor = _actor(request)
    row = await session.get(RemediationActionTable, action_id)
    if row is None or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Remediation action not found.")
    if body.status == "accepted_risk":
        note = body.deferred_note if body.deferred_note is not None else row.deferred_note
        if not (note and str(note).strip()):
            raise HTTPException(
                status_code=400,
                detail="deferred_note is required when status is accepted_risk",
            )
    prev_status = row.status
    if body.title is not None:
        row.title = body.title
    if body.description is not None:
        row.description = body.description
    if body.priority is not None:
        row.priority = body.priority
    if body.owner is not None:
        row.owner = body.owner
    if body.due_at_utc is not None:
        row.due_at_utc = body.due_at_utc
    if body.deferred_note is not None:
        row.deferred_note = body.deferred_note
    if body.status is not None:
        row.status = body.status
    row.updated_at_utc = datetime.now(UTC)
    hist_note: str | None = None
    if body.status_change_note is not None:
        stripped = body.status_change_note.strip()
        hist_note = stripped if stripped else None
    if body.status is not None and body.status != prev_status:
        session.add(
            RemediationStatusHistoryTable(
                id=str(uuid4()),
                tenant_id=tenant_id,
                action_id=action_id,
                from_status=prev_status,
                to_status=body.status,
                changed_at_utc=row.updated_at_utc,
                changed_by=actor,
                note=hist_note,
            )
        )
    await _audit_event(
        session,
        tenant_id=tenant_id,
        actor=actor,
        action=GovernanceAuditAction.REMEDIATION_ACTION_UPDATE.value,
        entity_id=action_id,
        payload={"patch": body.model_dump(exclude_none=True)},
    )
    await session.commit()
    return await get_remediation_action(action_id, tenant_id, session)


@router.post(
    "/{action_id}/comments",
    response_model=RemediationCommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def post_remediation_comment(
    action_id: str,
    body: RemediationCommentCreate,
    request: Request,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> RemediationCommentRead:
    actor = _actor(request)
    row = await session.get(RemediationActionTable, action_id)
    if row is None or row.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Remediation action not found.")
    cid = str(uuid4())
    now = datetime.now(UTC)
    session.add(
        RemediationCommentTable(
            id=cid,
            tenant_id=tenant_id,
            action_id=action_id,
            body=body.body,
            created_by=actor,
            created_at_utc=now,
        )
    )
    row.updated_at_utc = now
    await _audit_event(
        session,
        tenant_id=tenant_id,
        actor=actor,
        action=GovernanceAuditAction.REMEDIATION_ACTION_COMMENT.value,
        entity_id=action_id,
        payload={"comment_id": cid},
    )
    await session.commit()
    return RemediationCommentRead(
        id=cid,
        body=body.body,
        created_by=actor,
        created_at_utc=now,
    )
