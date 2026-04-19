from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.governance_audit_readiness_models import (
    AuditEvidenceGapRow,
    AuditReadinessControlRow,
    AuditReadinessFrameworkSlice,
    AuditReadinessSummaryRead,
    GovernanceAuditCaseCreate,
    GovernanceAuditCaseRead,
)
from app.models_db import (
    GovernanceAuditCaseControlTable,
    GovernanceAuditCaseFrameworkTable,
    GovernanceAuditCaseTable,
    GovernanceControlEvidenceTable,
    GovernanceControlTable,
    GovernanceEvidenceRequirementTable,
)
from app.repositories.governance_controls import GovernanceControlRepository
from app.services.governance_audit_readiness_rules import (
    ControlSignals,
    compute_control_metrics,
    normalize_framework_tag,
)


class GovernanceAuditReadinessRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def _tenant_req_index(self, tenant_id: str) -> dict[str, list[tuple[str, str, int]]]:
        stmt = select(GovernanceEvidenceRequirementTable).where(
            GovernanceEvidenceRequirementTable.tenant_id == tenant_id,
        )
        rows = self._s.scalars(stmt).all()
        idx: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
        for r in rows:
            fw = normalize_framework_tag(r.framework_tag)
            idx[fw].append((r.evidence_type_key, r.label, int(r.priority or 2)))
        return dict(idx)

    def list_cases(self, tenant_id: str, *, limit: int = 200) -> list[GovernanceAuditCaseRead]:
        stmt = (
            select(GovernanceAuditCaseTable)
            .where(GovernanceAuditCaseTable.tenant_id == tenant_id)
            .order_by(GovernanceAuditCaseTable.updated_at_utc.desc())
            .limit(limit)
        )
        rows = self._s.scalars(stmt).all()
        return [self._case_read(r.id, tenant_id) for r in rows]

    def _framework_tags(self, tenant_id: str, audit_case_id: str) -> list[str]:
        stmt = select(GovernanceAuditCaseFrameworkTable).where(
            GovernanceAuditCaseFrameworkTable.tenant_id == tenant_id,
            GovernanceAuditCaseFrameworkTable.audit_case_id == audit_case_id,
        )
        return [r.framework_tag for r in self._s.scalars(stmt).all()]

    def _control_ids(self, tenant_id: str, audit_case_id: str) -> list[str]:
        stmt = select(GovernanceAuditCaseControlTable).where(
            GovernanceAuditCaseControlTable.tenant_id == tenant_id,
            GovernanceAuditCaseControlTable.audit_case_id == audit_case_id,
        )
        return [r.control_id for r in self._s.scalars(stmt).all()]

    def _case_read(self, audit_case_id: str, tenant_id: str) -> GovernanceAuditCaseRead:
        row = self._s.get(GovernanceAuditCaseTable, audit_case_id)
        assert row is not None and row.tenant_id == tenant_id
        return GovernanceAuditCaseRead(
            id=row.id,
            tenant_id=row.tenant_id,
            title=row.title,
            description=row.description,
            status=row.status,
            framework_tags=self._framework_tags(tenant_id, audit_case_id),
            control_ids=self._control_ids(tenant_id, audit_case_id),
            created_at_utc=row.created_at_utc,
            updated_at_utc=row.updated_at_utc,
            created_by=row.created_by,
        )

    def get_case(self, tenant_id: str, audit_case_id: str) -> GovernanceAuditCaseRead | None:
        row = self._s.get(GovernanceAuditCaseTable, audit_case_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return self._case_read(audit_case_id, tenant_id)

    def _auto_attach_controls(
        self,
        tenant_id: str,
        audit_case_id: str,
        framework_tags: list[str],
    ) -> None:
        ctrl_repo = GovernanceControlRepository(self._s)
        want = {normalize_framework_tag(t) for t in framework_tags}
        now = datetime.now(UTC)
        offset = 0
        page_limit = 1000
        while True:
            items, total = ctrl_repo.list_controls_page(
                tenant_id,
                framework_tag=None,
                search=None,
                offset=offset,
                limit=page_limit,
            )
            if not items:
                break
            for c in items:
                tags = {normalize_framework_tag(t) for t in c.framework_tags}
                if want & tags:
                    self._attach_control_row(tenant_id, audit_case_id, c.id, now)
            offset += len(items)
            if offset >= total:
                break

    def _attach_control_row(
        self,
        tenant_id: str,
        audit_case_id: str,
        control_id: str,
        now: datetime,
    ) -> None:
        exists = self._s.scalars(
            select(GovernanceAuditCaseControlTable).where(
                GovernanceAuditCaseControlTable.tenant_id == tenant_id,
                GovernanceAuditCaseControlTable.audit_case_id == audit_case_id,
                GovernanceAuditCaseControlTable.control_id == control_id,
            )
        ).first()
        if exists is not None:
            return
        self._s.add(
            GovernanceAuditCaseControlTable(
                id=str(uuid4()),
                tenant_id=tenant_id,
                audit_case_id=audit_case_id,
                control_id=control_id,
                attached_at_utc=now,
            )
        )

    def create_case(
        self,
        tenant_id: str,
        body: GovernanceAuditCaseCreate,
        *,
        created_by: str | None,
    ) -> GovernanceAuditCaseRead:
        now = datetime.now(UTC)
        aid = str(uuid4())
        row = GovernanceAuditCaseTable(
            id=aid,
            tenant_id=tenant_id,
            title=body.title,
            description=body.description,
            status="active",
            created_at_utc=now,
            updated_at_utc=now,
            created_by=created_by,
        )
        self._s.add(row)
        seen_fw: set[str] = set()
        for ft in body.framework_tags:
            n = normalize_framework_tag(ft)[:64]
            if n in seen_fw:
                continue
            seen_fw.add(n)
            self._s.add(
                GovernanceAuditCaseFrameworkTable(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    audit_case_id=aid,
                    framework_tag=n,
                )
            )
        if body.control_ids is not None:
            ctrl_repo = GovernanceControlRepository(self._s)
            seen_control_ids: set[str] = set()
            for cid in body.control_ids:
                normalized_cid = cid.strip()
                if not normalized_cid or normalized_cid in seen_control_ids:
                    continue
                seen_control_ids.add(normalized_cid)
                if ctrl_repo.get_control(tenant_id, normalized_cid) is None:
                    raise ValueError(f"Unknown control_id for tenant: {normalized_cid}")
                self._attach_control_row(tenant_id, aid, normalized_cid, now)
        else:
            self._auto_attach_controls(tenant_id, aid, body.framework_tags)
        self._s.flush()
        return self._case_read(aid, tenant_id)

    def attach_control(
        self, tenant_id: str, audit_case_id: str, control_id: str
    ) -> GovernanceAuditCaseRead | None:
        if self.get_case(tenant_id, audit_case_id) is None:
            return None
        cr = GovernanceControlRepository(self._s)
        if cr.get_control(tenant_id, control_id) is None:
            return None
        self._attach_control_row(tenant_id, audit_case_id, control_id, datetime.now(UTC))
        ac = self._s.get(GovernanceAuditCaseTable, audit_case_id)
        assert ac is not None
        ac.updated_at_utc = datetime.now(UTC)
        self._s.flush()
        return self._case_read(audit_case_id, tenant_id)

    def _evidence_types_for_control(self, tenant_id: str, control_id: str) -> list[str]:
        stmt = select(GovernanceControlEvidenceTable).where(
            GovernanceControlEvidenceTable.tenant_id == tenant_id,
            GovernanceControlEvidenceTable.control_id == control_id,
        )
        return [r.source_type for r in self._s.scalars(stmt).all()]

    def build_readiness(
        self, tenant_id: str, audit_case_id: str
    ) -> AuditReadinessSummaryRead | None:
        case = self.get_case(tenant_id, audit_case_id)
        if case is None:
            return None
        cfw = {normalize_framework_tag(x) for x in case.framework_tags}
        req_idx = self._tenant_req_index(tenant_id)
        now = datetime.now(UTC)
        ctrl_repo = GovernanceControlRepository(self._s)

        controls_ready = 0
        gap_rows: list[AuditEvidenceGapRow] = []
        overdue_reviews = 0
        fw_stats: dict[str, dict[str, int]] = {
            fw: {"in": 0, "ready": 0, "gaps": 0} for fw in sorted(cfw)
        }

        for cid in case.control_ids:
            row = self._s.get(GovernanceControlTable, cid)
            if row is None or row.tenant_id != tenant_id:
                continue
            read = ctrl_repo.get_control(tenant_id, cid)
            if read is None:
                continue
            sig = ControlSignals(
                control_id=cid,
                title=read.title,
                framework_tags=list(read.framework_tags),
                status=read.status,
                owner=read.owner,
                next_review_at=read.next_review_at,
                evidence_source_types=self._evidence_types_for_control(tenant_id, cid),
            )
            comp, missing, ready, ro, gap_detail = compute_control_metrics(sig, cfw, req_idx, now)
            if ready:
                controls_ready += 1
            if ro:
                overdue_reviews += 1
            tags = {normalize_framework_tag(t) for t in read.framework_tags}
            for fw in sorted(cfw & tags):
                fw_stats[fw]["in"] += 1
                if ready:
                    fw_stats[fw]["ready"] += 1
            for gfw, ek, lab, pr in gap_detail:
                fw_stats[gfw]["gaps"] += 1
                gap_rows.append(
                    AuditEvidenceGapRow(
                        control_id=cid,
                        control_title=read.title,
                        missing_evidence_type_key=ek,
                        label_hint=lab,
                        priority=min(3, max(1, pr)),
                        recommended_action_de=(
                            f"Nachweis vom Typ „{lab}“ hinterlegen (source_type≈{ek})."
                        ),
                    )
                )

        total = len(case.control_ids)
        overall = 100.0 if total == 0 else round(100.0 * controls_ready / total, 1)
        by_fw = [
            AuditReadinessFrameworkSlice(
                framework_tag=fw,
                controls_in_scope=st["in"],
                controls_ready=st["ready"],
                evidence_gap_count=st["gaps"],
                readiness_pct=(
                    100.0 if st["in"] == 0 else round(100.0 * st["ready"] / st["in"], 1)
                ),
            )
            for fw, st in sorted(fw_stats.items())
        ]
        return AuditReadinessSummaryRead(
            audit_case_id=audit_case_id,
            overall_readiness_pct=overall,
            controls_total=total,
            controls_ready=controls_ready,
            evidence_gap_count=len(gap_rows),
            overdue_reviews_count=overdue_reviews,
            by_framework=by_fw,
            gaps=gap_rows,
        )

    def list_control_rows(
        self, tenant_id: str, audit_case_id: str
    ) -> list[AuditReadinessControlRow] | None:
        case = self.get_case(tenant_id, audit_case_id)
        if case is None:
            return None
        cfw = {normalize_framework_tag(x) for x in case.framework_tags}
        req_idx = self._tenant_req_index(tenant_id)
        now = datetime.now(UTC)
        ctrl_repo = GovernanceControlRepository(self._s)
        out: list[AuditReadinessControlRow] = []
        for cid in case.control_ids:
            read = ctrl_repo.get_control(tenant_id, cid)
            if read is None:
                continue
            sig = ControlSignals(
                control_id=cid,
                title=read.title,
                framework_tags=list(read.framework_tags),
                status=read.status,
                owner=read.owner,
                next_review_at=read.next_review_at,
                evidence_source_types=self._evidence_types_for_control(tenant_id, cid),
            )
            comp, missing, ready, ro, _ = compute_control_metrics(sig, cfw, req_idx, now)
            out.append(
                AuditReadinessControlRow(
                    control_id=cid,
                    title=read.title,
                    framework_tags=list(read.framework_tags),
                    status=read.status,
                    owner=read.owner,
                    evidence_completeness_pct=comp,
                    missing_evidence_types=missing,
                    next_review_at=read.next_review_at,
                    is_ready=ready,
                    review_overdue=ro,
                )
            )
        return out
