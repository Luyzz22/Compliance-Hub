"""NIS2 Art. 21 Incident Response Workflow Repository.

Mandantenfähig: Alle Queries filtern strikt nach tenant_id (RLS-konform).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.governance_taxonomy import NIS2DeadlinePolicy
from app.models_db import NIS2IncidentTable
from app.nis2_incident_models import (
    VALID_TRANSITIONS,
    NIS2IncidentCreate,
    NIS2IncidentDeadlinesOverride,
    NIS2IncidentResponse,
    NIS2IncidentTransition,
    NIS2WorkflowStatus,
)


class NIS2IncidentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_response(row: NIS2IncidentTable) -> NIS2IncidentResponse:
        now = datetime.now(UTC)
        closed = row.closed_at is not None

        def _as_utc(dt: datetime | None) -> datetime | None:
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)

        def _deadline_overdue(deadline: datetime | None) -> bool:
            d = _as_utc(deadline)
            return bool(d is not None and not closed and now > d)

        return NIS2IncidentResponse(
            id=row.id,
            tenant_id=row.tenant_id,
            title=row.title,
            incident_type=row.incident_type,
            severity=row.severity,
            workflow_status=row.workflow_status,
            summary=row.summary,
            affected_systems=json.loads(row.affected_systems_json),
            kritis_relevant=row.kritis_relevant,
            personal_data_affected=row.personal_data_affected,
            estimated_impact=row.estimated_impact,
            bsi_notification_deadline=row.bsi_notification_deadline,
            bsi_report_deadline=row.bsi_report_deadline,
            final_report_deadline=row.final_report_deadline,
            notification_deadline_overdue=_deadline_overdue(row.bsi_notification_deadline),
            report_deadline_overdue=_deadline_overdue(row.bsi_report_deadline),
            final_report_deadline_overdue=_deadline_overdue(row.final_report_deadline),
            detected_at=row.detected_at,
            contained_at=row.contained_at,
            eradicated_at=row.eradicated_at,
            recovered_at=row.recovered_at,
            closed_at=row.closed_at,
            created_by=row.created_by,
        )

    def create(
        self,
        tenant_id: str,
        data: NIS2IncidentCreate,
        created_by: str | None = None,
    ) -> NIS2IncidentResponse:
        now = datetime.now(UTC)
        report_deadline = now + timedelta(hours=NIS2DeadlinePolicy.REPORT_HOURS)
        row = NIS2IncidentTable(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            title=data.title,
            incident_type=data.incident_type.value,
            severity=data.severity,
            workflow_status=NIS2WorkflowStatus.DETECTED.value,
            summary=data.summary,
            affected_systems_json=json.dumps(data.affected_systems),
            kritis_relevant=data.kritis_relevant,
            personal_data_affected=data.personal_data_affected,
            estimated_impact=data.estimated_impact,
            bsi_notification_deadline=now + timedelta(hours=NIS2DeadlinePolicy.NOTIFICATION_HOURS),
            bsi_report_deadline=report_deadline,
            final_report_deadline=report_deadline
            + timedelta(days=NIS2DeadlinePolicy.FINAL_REPORT_DAYS_AFTER_REPORT),
            detected_at=now,
            created_by=created_by,
            created_at_utc=now,
            updated_at_utc=now,
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_response(row)

    def get(self, tenant_id: str, incident_id: str) -> NIS2IncidentResponse | None:
        stmt = select(NIS2IncidentTable).where(
            NIS2IncidentTable.tenant_id == tenant_id,
            NIS2IncidentTable.id == incident_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return self._to_response(row)

    def list_for_tenant(self, tenant_id: str, limit: int = 50) -> list[NIS2IncidentResponse]:
        stmt = (
            select(NIS2IncidentTable)
            .where(NIS2IncidentTable.tenant_id == tenant_id)
            .order_by(NIS2IncidentTable.created_at_utc.desc())
            .limit(limit)
        )
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_response(row) for row in rows]

    def transition(
        self,
        tenant_id: str,
        incident_id: str,
        transition: NIS2IncidentTransition,
    ) -> NIS2IncidentResponse:
        stmt = select(NIS2IncidentTable).where(
            NIS2IncidentTable.tenant_id == tenant_id,
            NIS2IncidentTable.id == incident_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise LookupError(f"NIS2 incident {incident_id} not found")

        current = NIS2WorkflowStatus(row.workflow_status)
        target = transition.target_status
        allowed = VALID_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise ValueError(
                f"Invalid transition from {current.value} to {target.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        now = datetime.now(UTC)
        row.workflow_status = target.value
        row.updated_at_utc = now

        timestamp_map: dict[NIS2WorkflowStatus, str] = {
            NIS2WorkflowStatus.CONTAINED: "contained_at",
            NIS2WorkflowStatus.ERADICATED: "eradicated_at",
            NIS2WorkflowStatus.RECOVERED: "recovered_at",
            NIS2WorkflowStatus.CLOSED: "closed_at",
        }
        attr = timestamp_map.get(target)
        if attr:
            setattr(row, attr, now)

        self._session.commit()
        self._session.refresh(row)
        return self._to_response(row)

    def override_deadlines(
        self,
        tenant_id: str,
        incident_id: str,
        body: NIS2IncidentDeadlinesOverride,
    ) -> NIS2IncidentResponse:
        stmt = select(NIS2IncidentTable).where(
            NIS2IncidentTable.tenant_id == tenant_id,
            NIS2IncidentTable.id == incident_id,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            raise LookupError(f"NIS2 incident {incident_id} not found")

        if body.bsi_notification_deadline is not None:
            row.bsi_notification_deadline = body.bsi_notification_deadline
        if body.bsi_report_deadline is not None:
            row.bsi_report_deadline = body.bsi_report_deadline
        if body.final_report_deadline is not None:
            row.final_report_deadline = body.final_report_deadline
        row.updated_at_utc = datetime.now(UTC)

        self._session.commit()
        self._session.refresh(row)
        return self._to_response(row)
