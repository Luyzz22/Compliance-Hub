"""Board Reporting & Management Pack APIs (tenant-scoped, deterministic, snapshot-first)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_dependencies import get_api_key_and_tenant
from app.board_reporting_models import (
    BoardActionRead,
    BoardMetricRead,
    BoardReportDetailRead,
    BoardReportGenerateRequest,
    BoardReportListItemRead,
    BoardReportSummaryRead,
)
from app.db_tenant import get_async_db
from app.governance_taxonomy import GovernanceAuditAction, GovernanceAuditEntity
from app.models_db import (
    AuditLogTable,
    BoardReportActionTable,
    BoardReportItemTable,
    BoardReportMetricHistoryTable,
    BoardReportSnapshotTable,
    BoardReportTable,
    GovernanceControlReviewTable,
    GovernanceControlTable,
    ServiceHealthIncidentTable,
)
from app.services.board_reporting_service import compute_snapshot, derive_period_bounds

router = APIRouter(prefix="/api/v1/governance/board-reports", tags=["governance", "board-reporting"])


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
            entity_type=GovernanceAuditEntity.BOARD_REPORT.value,
            entity_id=entity_id,
            after=json.dumps(payload),
            outcome="success",
            actor_role="compliance_officer",
            created_at_utc=datetime.now(UTC),
        )
    )


@router.get("", response_model=list[BoardReportListItemRead])
async def list_board_reports(
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> list[BoardReportListItemRead]:
    stmt = (
        select(BoardReportTable)
        .where(BoardReportTable.tenant_id == tenant_id)
        .order_by(BoardReportTable.generated_at_utc.desc())
        .limit(100)
    )
    rows = (await session.scalars(stmt)).all()
    return [
        BoardReportListItemRead(
            id=r.id,
            tenant_id=r.tenant_id,
            period_key=r.period_key,
            period_type=r.period_type,
            title=r.title,
            status=r.status,
            generated_at_utc=r.generated_at_utc,
            generated_by=r.generated_by,
        )
        for r in rows
    ]


@router.post("/generate", response_model=BoardReportDetailRead, status_code=status.HTTP_201_CREATED)
async def generate_board_report(
    body: BoardReportGenerateRequest,
    request: Request,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> BoardReportDetailRead:
    prev_start, prev_end = await derive_period_bounds(body.period_start, body.period_end)
    snapshot = await compute_snapshot(
        session,
        tenant_id=tenant_id,
        period_start=body.period_start,
        period_end=body.period_end,
        prev_start=prev_start,
        prev_end=prev_end,
    )
    report_id = str(uuid4())
    now = datetime.now(UTC)
    title = body.title or f"Management Pack {body.period_key}"
    actor = request.headers.get("x-actor-id", "api:governance-board-report")
    report = BoardReportTable(
        id=report_id,
        tenant_id=tenant_id,
        period_key=body.period_key,
        period_type=body.period_type,
        period_start=body.period_start,
        period_end=body.period_end,
        title=title,
        status="generated",
        generated_at_utc=now,
        generated_by=actor,
        created_at=now,
        updated_at=now,
    )
    session.add(report)
    session.add(
        BoardReportSnapshotTable(
            id=str(uuid4()),
            tenant_id=tenant_id,
            report_id=report_id,
            snapshot_kind="full",
            payload_json={
                "headline_de": snapshot.headline_de,
                "top_risk_areas": snapshot.top_risk_areas,
                "resilience_summary_de": snapshot.resilience_summary_de,
                "metrics": [
                    {
                        "metric_key": m.metric_key,
                        "label": m.label,
                        "value": m.value,
                        "unit": m.unit,
                        "traffic_light": m.traffic_light,
                        "trend_direction": m.trend_direction,
                        "trend_delta": m.trend_delta,
                        "narrative_de": m.narrative_de,
                    }
                    for m in snapshot.metrics
                ],
            },
            created_at=now,
        )
    )
    for idx, metric in enumerate(snapshot.metrics):
        session.add(
            BoardReportItemTable(
                id=str(uuid4()),
                tenant_id=tenant_id,
                report_id=report_id,
                item_type="metric",
                item_key=metric.metric_key,
                label=metric.label,
                value_num=metric.value,
                value_text=metric.narrative_de,
                unit=metric.unit,
                traffic_light=metric.traffic_light,
                trend_direction=metric.trend_direction,
                trend_delta=metric.trend_delta,
                sort_order=idx,
                created_at=now,
            )
        )
        session.add(
            BoardReportMetricHistoryTable(
                id=str(uuid4()),
                tenant_id=tenant_id,
                report_id=report_id,
                metric_key=metric.metric_key,
                period_start=body.period_start,
                period_end=body.period_end,
                value_num=metric.value,
                created_at=now,
            )
        )

    top_overdue_stmt = (
        select(GovernanceControlReviewTable, GovernanceControlTable)
        .join(
            GovernanceControlTable,
            GovernanceControlTable.id == GovernanceControlReviewTable.control_id,
        )
        .where(
            GovernanceControlReviewTable.tenant_id == tenant_id,
            GovernanceControlReviewTable.completed_at.is_(None),
            GovernanceControlReviewTable.due_at < body.period_end,
        )
        .order_by(GovernanceControlReviewTable.due_at.asc())
        .limit(5)
    )
    for review, control in (await session.execute(top_overdue_stmt)).all():
        session.add(
            BoardReportActionTable(
                id=str(uuid4()),
                tenant_id=tenant_id,
                report_id=report_id,
                action_title=f"Review abschließen: {control.title}",
                action_detail="Überfälliges Review aus Unified Control Layer.",
                owner=control.owner,
                due_at=review.due_at,
                status="open",
                priority="high",
                source_type="governance_control_review",
                source_id=review.id,
                created_at=now,
            )
        )

    critical_incident_stmt = (
        select(ServiceHealthIncidentTable)
        .where(
            ServiceHealthIncidentTable.tenant_id == tenant_id,
            ServiceHealthIncidentTable.incident_state == "open",
            ServiceHealthIncidentTable.severity == "critical",
        )
        .order_by(ServiceHealthIncidentTable.detected_at.asc())
        .limit(3)
    )
    for incident in (await session.scalars(critical_incident_stmt)).all():
        session.add(
            BoardReportActionTable(
                id=str(uuid4()),
                tenant_id=tenant_id,
                report_id=report_id,
                action_title=f"Incident adressieren: {incident.service_name}",
                action_detail=incident.title,
                owner=None,
                due_at=None,
                status="open",
                priority="high",
                source_type="service_health_incident",
                source_id=incident.id,
                created_at=now,
            )
        )

    await _audit_event(
        session,
        tenant_id=tenant_id,
        actor=actor,
        action=GovernanceAuditAction.BOARD_REPORT_GENERATE.value,
        entity_id=report_id,
        payload={"period_key": body.period_key, "period_type": body.period_type},
    )
    await session.commit()
    return await get_board_report(report_id, tenant_id=tenant_id, session=session)


@router.get("/{report_id}", response_model=BoardReportDetailRead)
async def get_board_report(
    report_id: str,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> BoardReportDetailRead:
    row = await session.scalar(
        select(BoardReportTable).where(
            BoardReportTable.id == report_id,
            BoardReportTable.tenant_id == tenant_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board report not found")

    snap = await session.scalar(
        select(BoardReportSnapshotTable)
        .where(
            BoardReportSnapshotTable.report_id == report_id,
            BoardReportSnapshotTable.tenant_id == tenant_id,
        )
        .order_by(BoardReportSnapshotTable.created_at.desc())
    )
    payload = snap.payload_json if snap else {}
    metric_rows = (await session.scalars(
        select(BoardReportItemTable)
        .where(
            BoardReportItemTable.report_id == report_id,
            BoardReportItemTable.tenant_id == tenant_id,
            BoardReportItemTable.item_type == "metric",
        )
        .order_by(BoardReportItemTable.sort_order.asc())
    )).all()
    metrics = [
        BoardMetricRead(
            metric_key=m.item_key,
            label=m.label,
            value=float(m.value_num or 0),
            unit=m.unit or "count",
            traffic_light=(m.traffic_light or "green"),
            trend_direction=(m.trend_direction or "stable"),
            trend_delta=float(m.trend_delta or 0),
            narrative_de=m.value_text,
        )
        for m in metric_rows
    ]
    actions = (await session.scalars(
        select(BoardReportActionTable)
        .where(
            BoardReportActionTable.report_id == report_id,
            BoardReportActionTable.tenant_id == tenant_id,
        )
        .order_by(BoardReportActionTable.priority.asc(), BoardReportActionTable.created_at.desc())
    )).all()
    audit_rows = (await session.scalars(
        select(AuditLogTable)
        .where(
            AuditLogTable.tenant_id == tenant_id,
            AuditLogTable.entity_type == GovernanceAuditEntity.BOARD_REPORT.value,
            AuditLogTable.entity_id == report_id,
        )
        .order_by(AuditLogTable.created_at_utc.desc())
        .limit(50)
    )).all()
    summary = BoardReportSummaryRead(
        report_id=report_id,
        period_key=row.period_key,
        period_type=row.period_type,
        generated_at_utc=row.generated_at_utc,
        headline_de=str(payload.get("headline_de") or "Management Pack"),
        top_risk_areas=list(payload.get("top_risk_areas") or []),
        metrics=metrics,
        resilience_summary_de=str(payload.get("resilience_summary_de") or ""),
    )
    return BoardReportDetailRead(
        id=row.id,
        tenant_id=row.tenant_id,
        period_key=row.period_key,
        period_type=row.period_type,
        period_start=row.period_start,
        period_end=row.period_end,
        title=row.title,
        status=row.status,
        generated_at_utc=row.generated_at_utc,
        generated_by=row.generated_by,
        summary=summary,
        actions=[
            BoardActionRead(
                id=a.id,
                action_title=a.action_title,
                action_detail=a.action_detail,
                owner=a.owner,
                due_at=a.due_at,
                status=a.status,
                priority=a.priority,
                source_type=a.source_type,
                source_id=a.source_id,
            )
            for a in actions
        ],
        audit_trail=[
            {
                "created_at_utc": r.created_at_utc.isoformat(),
                "actor": r.actor,
                "action": r.action,
                "outcome": r.outcome or "",
            }
            for r in audit_rows
        ],
    )


@router.get("/{report_id}/summary", response_model=BoardReportSummaryRead)
async def get_board_report_summary(
    report_id: str,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> BoardReportSummaryRead:
    detail = await get_board_report(report_id, tenant_id=tenant_id, session=session)
    return detail.summary


@router.get("/{report_id}/actions", response_model=list[BoardActionRead])
async def get_board_report_actions(
    report_id: str,
    tenant_id: str = Depends(get_api_key_and_tenant),
    session: AsyncSession = Depends(get_async_db),
) -> list[BoardActionRead]:
    rows = (await session.scalars(
        select(BoardReportActionTable)
        .where(
            BoardReportActionTable.report_id == report_id,
            BoardReportActionTable.tenant_id == tenant_id,
        )
        .order_by(BoardReportActionTable.priority.asc(), BoardReportActionTable.created_at.desc())
    )).all()
    return [
        BoardActionRead(
            id=r.id,
            action_title=r.action_title,
            action_detail=r.action_detail,
            owner=r.owner,
            due_at=r.due_at,
            status=r.status,
            priority=r.priority,
            source_type=r.source_type,
            source_id=r.source_id,
        )
        for r in rows
    ]
