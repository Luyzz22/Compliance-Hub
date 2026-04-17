from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from app.models_db import ServiceHealthIncidentTable, ServiceHealthSnapshotTable, TenantDB


@dataclass
class ServiceHealthSnapshotRow:
    id: str
    tenant_id: str
    poll_run_id: str
    source: str
    service_name: str
    status: str
    checked_at: datetime
    raw_payload: str


@dataclass
class ServiceHealthIncidentRow:
    id: str
    tenant_id: str
    service_name: str
    previous_status: str | None
    current_status: str
    severity: str
    incident_state: str
    source: str
    detected_at: datetime
    resolved_at: datetime | None
    title: str
    summary: str


class ServiceHealthRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_tenant_ids(self) -> list[str]:
        stmt = select(TenantDB.id)
        return list(self._session.scalars(stmt).all())

    def last_status_for_service(self, tenant_id: str, service_name: str) -> str | None:
        stmt: Select[tuple[str]] = (
            select(ServiceHealthSnapshotTable.status)
            .where(
                ServiceHealthSnapshotTable.tenant_id == tenant_id,
                ServiceHealthSnapshotTable.service_name == service_name,
            )
            .order_by(ServiceHealthSnapshotTable.checked_at.desc())
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def insert_snapshot(
        self,
        *,
        tenant_id: str,
        poll_run_id: str,
        service_name: str,
        status: str,
        checked_at: datetime,
        raw_payload: dict,
        source: str = "internal_health_poll",
    ) -> str:
        sid = str(uuid4())
        row = ServiceHealthSnapshotTable(
            id=sid,
            tenant_id=tenant_id,
            poll_run_id=poll_run_id,
            source=source,
            service_name=service_name,
            status=status,
            checked_at=checked_at,
            raw_payload=json.dumps(raw_payload, default=str),
        )
        self._session.add(row)
        self._session.flush()
        return sid

    def insert_incident(
        self,
        *,
        tenant_id: str,
        service_name: str,
        previous_status: str | None,
        current_status: str,
        severity: str,
        source: str,
        detected_at: datetime,
        triggering_snapshot_id: str | None,
        title: str,
        summary: str,
    ) -> str:
        iid = str(uuid4())
        row = ServiceHealthIncidentTable(
            id=iid,
            tenant_id=tenant_id,
            service_name=service_name,
            previous_status=previous_status,
            current_status=current_status,
            severity=severity,
            incident_state="open",
            source=source,
            detected_at=detected_at,
            resolved_at=None,
            updated_at_utc=detected_at,
            triggering_snapshot_id=triggering_snapshot_id,
            title=title,
            summary=summary,
        )
        self._session.add(row)
        self._session.flush()
        return iid

    def resolve_open_incidents_for_service(
        self,
        tenant_id: str,
        service_name: str,
        when: datetime,
    ) -> int:
        stmt = (
            update(ServiceHealthIncidentTable)
            .where(
                ServiceHealthIncidentTable.tenant_id == tenant_id,
                ServiceHealthIncidentTable.service_name == service_name,
                ServiceHealthIncidentTable.incident_state == "open",
            )
            .values(
                incident_state="resolved",
                resolved_at=when,
                updated_at_utc=when,
            )
        )
        res = self._session.execute(stmt)
        return int(res.rowcount or 0)

    def list_snapshots(
        self,
        tenant_id: str,
        *,
        limit: int = 100,
    ) -> list[ServiceHealthSnapshotRow]:
        stmt = (
            select(ServiceHealthSnapshotTable)
            .where(ServiceHealthSnapshotTable.tenant_id == tenant_id)
            .order_by(ServiceHealthSnapshotTable.checked_at.desc())
            .limit(limit)
        )
        rows = self._session.scalars(stmt).all()
        return [
            ServiceHealthSnapshotRow(
                id=r.id,
                tenant_id=r.tenant_id,
                poll_run_id=r.poll_run_id,
                source=r.source,
                service_name=r.service_name,
                status=r.status,
                checked_at=r.checked_at,
                raw_payload=r.raw_payload,
            )
            for r in rows
        ]

    def list_incidents(
        self,
        tenant_id: str,
        *,
        open_only: bool = False,
        limit: int = 100,
    ) -> list[ServiceHealthIncidentRow]:
        stmt = select(ServiceHealthIncidentTable).where(
            ServiceHealthIncidentTable.tenant_id == tenant_id
        )
        if open_only:
            stmt = stmt.where(ServiceHealthIncidentTable.incident_state == "open")
        stmt = stmt.order_by(ServiceHealthIncidentTable.detected_at.desc()).limit(limit)
        rows = self._session.scalars(stmt).all()
        return [
            ServiceHealthIncidentRow(
                id=r.id,
                tenant_id=r.tenant_id,
                service_name=r.service_name,
                previous_status=r.previous_status,
                current_status=r.current_status,
                severity=r.severity,
                incident_state=r.incident_state,
                source=r.source,
                detected_at=r.detected_at,
                resolved_at=r.resolved_at,
                title=r.title,
                summary=r.summary,
            )
            for r in rows
        ]

    def get_incident(self, tenant_id: str, incident_id: str) -> ServiceHealthIncidentTable | None:
        stmt = select(ServiceHealthIncidentTable).where(
            ServiceHealthIncidentTable.id == incident_id,
            ServiceHealthIncidentTable.tenant_id == tenant_id,
        )
        return self._session.scalars(stmt).first()

    def mark_incident_resolved(self, tenant_id: str, incident_id: str, when: datetime) -> bool:
        row = self.get_incident(tenant_id, incident_id)
        if row is None or row.incident_state != "open":
            return False
        row.incident_state = "resolved"
        row.resolved_at = when
        row.updated_at_utc = when
        self._session.flush()
        return True

    def count_open_incidents(self, tenant_id: str) -> int:
        stmt = select(func.count()).select_from(ServiceHealthIncidentTable).where(
            ServiceHealthIncidentTable.tenant_id == tenant_id,
            ServiceHealthIncidentTable.incident_state == "open",
        )
        return int(self._session.execute(stmt).scalar_one())

    def latest_snapshot_statuses(self, tenant_id: str) -> dict[str, str]:
        """Latest status per logical service_name for KPI tiles."""
        # Per-service latest: fetch ordered rows and pick first per name (small N).
        stmt = select(ServiceHealthSnapshotTable).where(
            ServiceHealthSnapshotTable.tenant_id == tenant_id
        ).order_by(ServiceHealthSnapshotTable.checked_at.desc())
        rows = self._session.scalars(stmt).all()
        out: dict[str, str] = {}
        for r in rows:
            if r.service_name not in out:
                out[r.service_name] = r.status
        return out

    def last_checked_at(self, tenant_id: str) -> datetime | None:
        stmt = select(func.max(ServiceHealthSnapshotTable.checked_at)).where(
            ServiceHealthSnapshotTable.tenant_id == tenant_id
        )
        return self._session.execute(stmt).scalar_one_or_none()
