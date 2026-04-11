"""Enterprise audit trail service (Phase 10) – filtering, export, integrity."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models_db import AuditAlertDB, AuditLogTable
from app.repositories.audit_logs import AuditLogRepository, _compute_entry_hash
from app.services.audit_trail_types import (
    AuditAlertItem,
    AuditLogItem,
    AuditLogPage,
    ChainIntegrityResult,
    VVTEntry,
    VVTExport,
)


def _row_to_item(row: AuditLogTable) -> AuditLogItem:
    return AuditLogItem(
        id=row.id,
        tenant_id=row.tenant_id,
        actor=row.actor,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        before=row.before,
        after=row.after,
        ip_address=row.ip_address,
        user_agent=row.user_agent,
        previous_hash=row.previous_hash,
        entry_hash=row.entry_hash,
        created_at_utc=row.created_at_utc,
        actor_role=row.actor_role,
        outcome=row.outcome,
        correlation_id=row.correlation_id,
        metadata_json=row.metadata_json,
    )


class AuditTrailService:
    """High-level service for enterprise audit trail operations."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = AuditLogRepository(session)

    def list_filtered(
        self,
        tenant_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        actor: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> AuditLogPage:
        stmt = select(AuditLogTable).where(AuditLogTable.tenant_id == tenant_id)

        if actor:
            stmt = stmt.where(AuditLogTable.actor == actor)
        if action:
            stmt = stmt.where(AuditLogTable.action == action)
        if resource_type:
            stmt = stmt.where(AuditLogTable.entity_type == resource_type)
        if from_date:
            stmt = stmt.where(AuditLogTable.created_at_utc >= from_date)
        if to_date:
            stmt = stmt.where(AuditLogTable.created_at_utc <= to_date)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self._session.execute(count_stmt).scalar_one()

        # Paginate
        offset = (page - 1) * page_size
        data_stmt = (
            stmt.order_by(AuditLogTable.created_at_utc.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = self._session.execute(data_stmt).scalars().all()

        return AuditLogPage(
            items=[_row_to_item(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        )

    def verify_integrity(self, tenant_id: str) -> ChainIntegrityResult:
        stmt = (
            select(AuditLogTable)
            .where(AuditLogTable.tenant_id == tenant_id)
            .order_by(AuditLogTable.id.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        prev_hash: str | None = None
        for row in rows:
            if row.entry_hash is None:
                prev_hash = None
                continue
            if row.previous_hash != prev_hash:
                return ChainIntegrityResult(
                    valid=False, checked_count=len(rows), first_invalid_id=row.id
                )
            expected = _compute_entry_hash(
                tenant_id=row.tenant_id,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                before=row.before,
                after=row.after,
                created_at=row.created_at_utc,
                previous_hash=row.previous_hash,
            )
            if row.entry_hash != expected:
                return ChainIntegrityResult(
                    valid=False, checked_count=len(rows), first_invalid_id=row.id
                )
            prev_hash = row.entry_hash
        return ChainIntegrityResult(valid=True, checked_count=len(rows))

    def export_csv(self, tenant_id: str, limit: int = 10_000) -> str:
        entries = self._repo.list_for_tenant(tenant_id=tenant_id, limit=limit)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id",
            "timestamp",
            "actor",
            "actor_role",
            "action",
            "entity_type",
            "entity_id",
            "outcome",
            "ip_address",
            "user_agent",
            "entry_hash",
            "previous_hash",
        ])
        for e in entries:
            writer.writerow([
                e.id,
                e.created_at_utc.isoformat(),
                e.actor,
                e.actor_role or "",
                e.action,
                e.entity_type,
                e.entity_id,
                e.outcome or "",
                e.ip_address or "",
                e.user_agent or "",
                e.entry_hash or "",
                e.previous_hash or "",
            ])
        return buf.getvalue()

    def export_json(self, tenant_id: str, limit: int = 10_000) -> str:
        entries = self._repo.list_for_tenant(tenant_id=tenant_id, limit=limit)
        return json.dumps(
            [e.model_dump(mode="json") for e in entries],
            indent=2,
            default=str,
        )

    def generate_vvt_export(self, tenant_id: str) -> VVTExport:
        """Generate DSGVO Art. 30 Verarbeitungsverzeichnis from audit data."""
        entries = self._repo.list_for_tenant(tenant_id=tenant_id, limit=50_000)

        activity_map: dict[str, set[str]] = {}
        for entry in entries:
            key = entry.action
            if key not in activity_map:
                activity_map[key] = set()
            activity_map[key].add(entry.entity_type)

        vvt_entries: list[VVTEntry] = []
        for action_key, entity_types in sorted(activity_map.items()):
            vvt_entries.append(
                VVTEntry(
                    processing_activity=action_key,
                    data_categories=sorted(entity_types),
                    purpose=f"Compliance-Verarbeitung: {action_key}",
                    legal_basis="Art. 6 Abs. 1 lit. c/f DSGVO",
                    recipients=["Compliance-Hub System", "Tenant-Administratoren"],
                    retention_period="10 Jahre (GoBD §14b UStG)",
                    technical_measures=[
                        "SHA-256 Hashketten-Integrität",
                        "Append-only Speicherung",
                        "Row-Level-Security",
                        "TLS 1.3 Verschlüsselung",
                    ],
                )
            )

        return VVTExport(
            tenant_id=tenant_id,
            generated_at=datetime.now(UTC),
            entries=vvt_entries,
            total_processing_activities=len(vvt_entries),
        )


class NIS2AlertService:
    """NIS2 alert generation and management."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_alert(
        self,
        *,
        tenant_id: str,
        severity: str,
        alert_type: str,
        title: str,
        description: str | None = None,
        actor: str | None = None,
        ip_address: str | None = None,
        audit_log_id: int | None = None,
    ) -> AuditAlertItem:
        row = AuditAlertDB(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            audit_log_id=audit_log_id,
            severity=severity,
            alert_type=alert_type,
            title=title,
            description=description,
            actor=actor,
            ip_address=ip_address,
            created_at_utc=datetime.now(UTC),
        )
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return self._to_item(row)

    def list_alerts(
        self,
        tenant_id: str,
        *,
        severity: str | None = None,
        resolved: bool | None = None,
        limit: int = 100,
    ) -> list[AuditAlertItem]:
        stmt = select(AuditAlertDB).where(AuditAlertDB.tenant_id == tenant_id)
        if severity:
            stmt = stmt.where(AuditAlertDB.severity == severity)
        if resolved is not None:
            stmt = stmt.where(AuditAlertDB.resolved == resolved)
        stmt = stmt.order_by(AuditAlertDB.created_at_utc.desc()).limit(limit)
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_item(r) for r in rows]

    def resolve_alert(
        self, tenant_id: str, alert_id: str, resolved_by: str
    ) -> AuditAlertItem | None:
        row = self._session.get(AuditAlertDB, alert_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        row.resolved = True
        row.resolved_by = resolved_by
        row.resolved_at = datetime.now(UTC)
        self._session.commit()
        self._session.refresh(row)
        return self._to_item(row)

    @staticmethod
    def _to_item(row: AuditAlertDB) -> AuditAlertItem:
        return AuditAlertItem(
            id=row.id,
            tenant_id=row.tenant_id,
            audit_log_id=row.audit_log_id,
            severity=row.severity,
            alert_type=row.alert_type,
            title=row.title,
            description=row.description,
            actor=row.actor,
            ip_address=row.ip_address,
            resolved=row.resolved,
            resolved_by=row.resolved_by,
            resolved_at=row.resolved_at,
            created_at_utc=row.created_at_utc,
        )
