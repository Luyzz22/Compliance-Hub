from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.governance_control_models import (
    FrameworkMappingCreate,
    FrameworkMappingRead,
    GovernanceControlCreate,
    GovernanceControlEvidenceCreate,
    GovernanceControlEvidenceRead,
    GovernanceControlRead,
    GovernanceControlsDashboardSummary,
    GovernanceControlStatusHistoryRead,
    GovernanceControlUpdate,
)
from app.models_db import (
    GovernanceControlEvidenceTable,
    GovernanceControlFrameworkMappingTable,
    GovernanceControlStatusHistoryTable,
    GovernanceControlTable,
)


class GovernanceControlRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def _mappings_for(self, tenant_id: str, control_id: str) -> list[FrameworkMappingRead]:
        stmt = select(GovernanceControlFrameworkMappingTable).where(
            GovernanceControlFrameworkMappingTable.tenant_id == tenant_id,
            GovernanceControlFrameworkMappingTable.control_id == control_id,
        )
        rows = self._s.scalars(stmt).all()
        return [
            FrameworkMappingRead(
                id=r.id,
                framework=r.framework,
                clause_ref=r.clause_ref,
                mapping_note=r.mapping_note,
            )
            for r in rows
        ]

    def _row_to_read(self, row: GovernanceControlTable) -> GovernanceControlRead:
        tags = row.framework_tags_json if isinstance(row.framework_tags_json, list) else []
        src = row.source_inputs_json if isinstance(row.source_inputs_json, dict) else {}
        return GovernanceControlRead(
            id=row.id,
            tenant_id=row.tenant_id,
            requirement_id=row.requirement_id,
            title=row.title,
            description=row.description,
            status=row.status,
            owner=row.owner,
            next_review_at=row.next_review_at,
            framework_tags=list(tags),
            source_inputs=dict(src),
            created_at_utc=row.created_at_utc,
            updated_at_utc=row.updated_at_utc,
            created_by=row.created_by,
            framework_mappings=self._mappings_for(row.tenant_id, row.id),
        )

    _FILTER_SCAN_CAP = 5000

    def _base_stmt(self, tenant_id: str, *, search: str | None):
        stmt = select(GovernanceControlTable).where(GovernanceControlTable.tenant_id == tenant_id)
        if search and search.strip():
            q = f"%{search.strip()[:200]}%"
            stmt = stmt.where(GovernanceControlTable.title.ilike(q))
        return stmt.order_by(GovernanceControlTable.updated_at_utc.desc())

    def list_controls_page(
        self,
        tenant_id: str,
        *,
        framework_tag: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 200,
    ) -> tuple[list[GovernanceControlRead], int]:
        """
        Paginated list with accurate total when no framework_tag (SQL count + offset).

        With framework_tag, tags are filtered in-process (JSON array portability); total
        capped by _FILTER_SCAN_CAP for predictable cost on SQLite.
        """
        if framework_tag and framework_tag.strip():
            stmt = self._base_stmt(tenant_id, search=search).limit(self._FILTER_SCAN_CAP)
            rows = list(self._s.scalars(stmt).all())
            out = [self._row_to_read(r) for r in rows]
            tag = framework_tag.strip().upper()
            out = [c for c in out if any(t.upper() == tag for t in c.framework_tags)]
            total = len(out)
            return out[offset : offset + limit], total

        count_stmt = (
            select(func.count())
            .select_from(GovernanceControlTable)
            .where(GovernanceControlTable.tenant_id == tenant_id)
        )
        if search and search.strip():
            q = f"%{search.strip()[:200]}%"
            count_stmt = count_stmt.where(GovernanceControlTable.title.ilike(q))
        total = int(self._s.scalar(count_stmt) or 0)

        stmt = self._base_stmt(tenant_id, search=search).offset(offset).limit(limit)
        rows = self._s.scalars(stmt).all()
        return [self._row_to_read(r) for r in rows], total

    def list_controls(
        self,
        tenant_id: str,
        *,
        framework_tag: str | None = None,
        limit: int = 200,
    ) -> list[GovernanceControlRead]:
        items, _ = self.list_controls_page(
            tenant_id, framework_tag=framework_tag, search=None, offset=0, limit=limit
        )
        return items

    def get_control(self, tenant_id: str, control_id: str) -> GovernanceControlRead | None:
        stmt = select(GovernanceControlTable).where(
            GovernanceControlTable.tenant_id == tenant_id,
            GovernanceControlTable.id == control_id,
        )
        row = self._s.scalars(stmt).first()
        return self._row_to_read(row) if row else None

    def _insert_mappings(
        self,
        tenant_id: str,
        control_id: str,
        mappings: list[FrameworkMappingCreate],
    ) -> None:
        for m in mappings:
            self._s.add(
                GovernanceControlFrameworkMappingTable(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    control_id=control_id,
                    framework=m.framework[:64],
                    clause_ref=m.clause_ref[:256],
                    mapping_note=m.mapping_note,
                )
            )

    def _append_status_history(
        self,
        tenant_id: str,
        control_id: str,
        from_status: str | None,
        to_status: str,
        changed_by: str | None,
        note: str | None = None,
    ) -> None:
        self._s.add(
            GovernanceControlStatusHistoryTable(
                id=str(uuid4()),
                tenant_id=tenant_id,
                control_id=control_id,
                from_status=from_status,
                to_status=to_status,
                changed_at_utc=datetime.now(UTC),
                changed_by=changed_by,
                note=note,
            )
        )

    def create_control(
        self,
        tenant_id: str,
        body: GovernanceControlCreate,
        *,
        created_by: str | None,
    ) -> GovernanceControlRead:
        now = datetime.now(UTC)
        cid = str(uuid4())
        tags = [t[:64] for t in body.framework_tags]
        src = dict(body.source_inputs) if isinstance(body.source_inputs, dict) else {}
        row = GovernanceControlTable(
            id=cid,
            tenant_id=tenant_id,
            requirement_id=body.requirement_id,
            title=body.title,
            description=body.description,
            status=body.status,
            owner=body.owner,
            next_review_at=body.next_review_at,
            framework_tags_json=tags,
            source_inputs_json=src,
            created_at_utc=now,
            updated_at_utc=now,
            created_by=created_by,
        )
        self._s.add(row)
        self._insert_mappings(tenant_id, cid, body.framework_mappings)
        self._append_status_history(tenant_id, cid, None, body.status, created_by, "created")
        self._s.flush()
        return self._row_to_read(row)

    def update_control(
        self,
        tenant_id: str,
        control_id: str,
        body: GovernanceControlUpdate,
        *,
        changed_by: str | None,
    ) -> GovernanceControlRead | None:
        stmt = select(GovernanceControlTable).where(
            GovernanceControlTable.tenant_id == tenant_id,
            GovernanceControlTable.id == control_id,
        )
        row = self._s.scalars(stmt).first()
        if row is None:
            return None
        prev_status = row.status
        if body.title is not None:
            row.title = body.title
        if body.description is not None:
            row.description = body.description
        if body.status is not None:
            row.status = body.status
        if body.owner is not None:
            row.owner = body.owner
        if body.next_review_at is not None:
            row.next_review_at = body.next_review_at
        if body.framework_tags is not None:
            row.framework_tags_json = [t[:64] for t in body.framework_tags]
        row.updated_at_utc = datetime.now(UTC)
        if body.status is not None and body.status != prev_status:
            self._append_status_history(
                tenant_id,
                control_id,
                prev_status,
                body.status,
                changed_by,
                "status_change",
            )
        self._s.flush()
        return self._row_to_read(row)

    def add_evidence(
        self,
        tenant_id: str,
        control_id: str,
        body: GovernanceControlEvidenceCreate,
        *,
        created_by: str | None,
    ) -> GovernanceControlEvidenceRead | None:
        if self.get_control(tenant_id, control_id) is None:
            return None
        eid = str(uuid4())
        now = datetime.now(UTC)
        ev = GovernanceControlEvidenceTable(
            id=eid,
            tenant_id=tenant_id,
            control_id=control_id,
            title=body.title,
            body_text=body.body_text,
            source_type=body.source_type[:64],
            source_ref=body.source_ref[:256] if body.source_ref else None,
            created_at_utc=now,
            created_by=created_by,
        )
        self._s.add(ev)
        self._s.flush()
        return GovernanceControlEvidenceRead(
            id=eid,
            control_id=control_id,
            title=body.title,
            body_text=body.body_text,
            source_type=body.source_type,
            source_ref=body.source_ref,
            created_at_utc=now,
            created_by=created_by,
        )

    def list_evidence(self, tenant_id: str, control_id: str) -> list[GovernanceControlEvidenceRead]:
        if self.get_control(tenant_id, control_id) is None:
            return []
        stmt = (
            select(GovernanceControlEvidenceTable)
            .where(
                GovernanceControlEvidenceTable.tenant_id == tenant_id,
                GovernanceControlEvidenceTable.control_id == control_id,
            )
            .order_by(GovernanceControlEvidenceTable.created_at_utc.desc())
        )
        rows = self._s.scalars(stmt).all()
        return [
            GovernanceControlEvidenceRead(
                id=r.id,
                control_id=r.control_id,
                title=r.title,
                body_text=r.body_text,
                source_type=r.source_type,
                source_ref=r.source_ref,
                created_at_utc=r.created_at_utc,
                created_by=r.created_by,
            )
            for r in rows
        ]

    def list_status_history(
        self, tenant_id: str, control_id: str
    ) -> list[GovernanceControlStatusHistoryRead]:
        if self.get_control(tenant_id, control_id) is None:
            return []
        stmt = (
            select(GovernanceControlStatusHistoryTable)
            .where(
                GovernanceControlStatusHistoryTable.tenant_id == tenant_id,
                GovernanceControlStatusHistoryTable.control_id == control_id,
            )
            .order_by(GovernanceControlStatusHistoryTable.changed_at_utc.desc())
        )
        rows = self._s.scalars(stmt).all()
        return [
            GovernanceControlStatusHistoryRead(
                id=r.id,
                control_id=r.control_id,
                from_status=r.from_status,
                to_status=r.to_status,
                changed_at_utc=r.changed_at_utc,
                changed_by=r.changed_by,
                note=r.note,
            )
            for r in rows
        ]

    def find_materialized_suggestion(
        self, tenant_id: str, suggestion_key: str
    ) -> GovernanceControlRead | None:
        stmt = select(GovernanceControlTable).where(
            GovernanceControlTable.tenant_id == tenant_id,
        )
        for row in self._s.scalars(stmt).all():
            src = row.source_inputs_json if isinstance(row.source_inputs_json, dict) else {}
            if src.get("materialized_from_suggestion") == suggestion_key:
                return self._row_to_read(row)
        return None

    def list_controls_for_export(
        self, tenant_id: str, *, limit: int = 10000
    ) -> list[GovernanceControlRead]:
        stmt = (
            select(GovernanceControlTable)
            .where(GovernanceControlTable.tenant_id == tenant_id)
            .order_by(GovernanceControlTable.updated_at_utc.desc())
            .limit(min(limit, 50_000))
        )
        rows = self._s.scalars(stmt).all()
        return [self._row_to_read(r) for r in rows]

    def dashboard_summary(self, tenant_id: str) -> GovernanceControlsDashboardSummary:
        now = datetime.now(UTC)
        stmt = select(GovernanceControlTable).where(GovernanceControlTable.tenant_id == tenant_id)
        rows = list(self._s.scalars(stmt).all())
        total = len(rows)
        status_keys = ("implemented", "in_progress", "not_started", "needs_review", "overdue")
        counts = {s: 0 for s in status_keys}
        overdue = 0
        for row in rows:
            st = row.status
            if st in counts:
                counts[st] += 1
            else:
                counts["not_started"] += 1
            if (
                row.next_review_at is not None
                and row.next_review_at < now
                and row.status == "implemented"
            ):
                overdue += 1
        return GovernanceControlsDashboardSummary(
            total_controls=total,
            implemented=counts["implemented"],
            in_progress=counts["in_progress"],
            not_started=counts["not_started"],
            needs_review=counts["needs_review"],
            overdue_reviews=overdue,
        )
