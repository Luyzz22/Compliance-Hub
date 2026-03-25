"""Datenzugriff Regelwerksgraph / Cross-Regulation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import (
    ComplianceControlActionDB,
    ComplianceControlAISystemDB,
    ComplianceControlDB,
    ComplianceControlPolicyDB,
    ComplianceFrameworkDB,
    ComplianceRequirementControlLinkDB,
    ComplianceRequirementDB,
    ComplianceRequirementRelationDB,
)


class CrossRegulationRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def list_frameworks(self) -> list[ComplianceFrameworkDB]:
        stmt = select(ComplianceFrameworkDB).order_by(ComplianceFrameworkDB.id)
        return list(self._s.scalars(stmt))

    def get_framework_by_key(self, key: str) -> ComplianceFrameworkDB | None:
        return self._s.scalars(
            select(ComplianceFrameworkDB).where(ComplianceFrameworkDB.key == key)
        ).first()

    def list_requirements(
        self,
        *,
        framework_key: str | None = None,
    ) -> list[ComplianceRequirementDB]:
        stmt = select(ComplianceRequirementDB).join(ComplianceFrameworkDB)
        if framework_key:
            stmt = stmt.where(ComplianceFrameworkDB.key == framework_key)
        stmt = stmt.order_by(ComplianceFrameworkDB.key, ComplianceRequirementDB.code)
        return list(self._s.scalars(stmt))

    def get_requirement(self, requirement_id: int) -> ComplianceRequirementDB | None:
        return self._s.get(ComplianceRequirementDB, requirement_id)

    def list_controls(self, tenant_id: str) -> list[ComplianceControlDB]:
        return list(
            self._s.scalars(
                select(ComplianceControlDB)
                .where(ComplianceControlDB.tenant_id == tenant_id)
                .order_by(ComplianceControlDB.name)
            )
        )

    def list_control_ids_for_tenant(self, tenant_id: str) -> set[str]:
        rows = self._s.scalars(
            select(ComplianceControlDB.id).where(ComplianceControlDB.tenant_id == tenant_id)
        ).all()
        return set(rows)

    def map_requirement_links_for_tenant(self, tenant_id: str) -> dict[int, list[str]]:
        """requirement_id -> list of coverage_level for that tenant's controls."""
        control_ids = self.list_control_ids_for_tenant(tenant_id)
        if not control_ids:
            return {}
        stmt = select(
            ComplianceRequirementControlLinkDB.requirement_id,
            ComplianceRequirementControlLinkDB.coverage_level,
        ).where(ComplianceRequirementControlLinkDB.control_id.in_(control_ids))
        out: dict[int, list[str]] = defaultdict(list)
        for rid, level in self._s.execute(stmt):
            out[int(rid)].append(str(level))
        return dict(out)

    def map_links_detail_for_requirement(
        self,
        tenant_id: str,
        requirement_id: int,
    ) -> list[tuple[ComplianceRequirementControlLinkDB, ComplianceControlDB]]:
        control_ids = self.list_control_ids_for_tenant(tenant_id)
        if not control_ids:
            return []
        stmt = (
            select(ComplianceRequirementControlLinkDB, ComplianceControlDB)
            .join(
                ComplianceControlDB,
                ComplianceControlDB.id == ComplianceRequirementControlLinkDB.control_id,
            )
            .where(
                ComplianceRequirementControlLinkDB.requirement_id == requirement_id,
                ComplianceControlDB.tenant_id == tenant_id,
            )
        )
        return list(self._s.execute(stmt).all())

    def requirement_relation_neighbors(self, requirement_ids: Iterable[int]) -> dict[int, set[int]]:
        ids = {int(x) for x in requirement_ids}
        if not ids:
            return {}
        stmt = select(
            ComplianceRequirementRelationDB.source_requirement_id,
            ComplianceRequirementRelationDB.target_requirement_id,
        )
        neighbors: dict[int, set[int]] = defaultdict(set)
        for src, tgt in self._s.execute(stmt):
            s, t = int(src), int(tgt)
            if s in ids:
                neighbors[s].add(t)
            if t in ids:
                neighbors[t].add(s)
        return dict(neighbors)

    def framework_key_by_requirement_id(self) -> dict[int, str]:
        stmt = select(ComplianceRequirementDB.id, ComplianceFrameworkDB.key).join(
            ComplianceFrameworkDB,
            ComplianceFrameworkDB.id == ComplianceRequirementDB.framework_id,
        )
        return {int(rid): str(fk) for rid, fk in self._s.execute(stmt)}

    def ai_systems_for_controls(
        self,
        tenant_id: str,
        control_ids: Iterable[str],
    ) -> dict[str, list[str]]:
        cids = list(control_ids)
        if not cids:
            return {}
        cas = ComplianceControlAISystemDB
        stmt = select(cas.control_id, cas.ai_system_id).where(
            cas.tenant_id == tenant_id,
            cas.control_id.in_(cids),
        )
        out: dict[str, list[str]] = defaultdict(list)
        for cid, aid in self._s.execute(stmt):
            out[str(cid)].append(str(aid))
        return dict(out)

    def policies_for_controls(
        self,
        tenant_id: str,
        control_ids: Iterable[str],
    ) -> dict[str, list[str]]:
        cids = list(control_ids)
        if not cids:
            return {}
        ccp = ComplianceControlPolicyDB
        stmt = select(ccp.control_id, ccp.policy_id).where(
            ccp.tenant_id == tenant_id,
            ccp.control_id.in_(cids),
        )
        out: dict[str, list[str]] = defaultdict(list)
        for cid, pid in self._s.execute(stmt):
            out[str(cid)].append(str(pid))
        return dict(out)

    def actions_for_controls(
        self,
        tenant_id: str,
        control_ids: Iterable[str],
    ) -> dict[str, list[str]]:
        cids = list(control_ids)
        if not cids:
            return {}
        cca = ComplianceControlActionDB
        stmt = select(cca.control_id, cca.action_id).where(
            cca.tenant_id == tenant_id,
            cca.control_id.in_(cids),
        )
        out: dict[str, list[str]] = defaultdict(list)
        for cid, aid in self._s.execute(stmt):
            out[str(cid)].append(str(aid))
        return dict(out)

    def requirements_for_ai_system(self, tenant_id: str, ai_system_id: str) -> list[int]:
        stmt = (
            select(ComplianceRequirementControlLinkDB.requirement_id)
            .join(
                ComplianceControlDB,
                ComplianceControlDB.id == ComplianceRequirementControlLinkDB.control_id,
            )
            .join(
                ComplianceControlAISystemDB,
                ComplianceControlAISystemDB.control_id == ComplianceControlDB.id,
            )
            .where(
                ComplianceControlAISystemDB.tenant_id == tenant_id,
                ComplianceControlAISystemDB.ai_system_id == ai_system_id,
                ComplianceControlDB.tenant_id == tenant_id,
            )
            .distinct()
        )
        return [int(x) for x in self._s.scalars(stmt).all()]
