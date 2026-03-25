"""Cross-Regulation: Aggregationen und API-DTOs."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cross_regulation_models import (
    AISystemRegulatoryHintOut,
    CrossRegFrameworkSummary,
    CrossRegulationSummaryResponse,
    RegulatoryControlOut,
    RegulatoryFrameworkOut,
    RegulatoryRequirementOut,
    RequirementControlLinkDetail,
    RequirementControlsDetailResponse,
)
from app.models_db import (
    ComplianceControlAISystemDB,
    ComplianceControlDB,
    ComplianceFrameworkDB,
    ComplianceRequirementControlLinkDB,
    ComplianceRequirementDB,
)
from app.repositories.cross_regulation import CrossRegulationRepository
from app.services.cross_regulation_coverage import (
    best_coverage_levels_for_requirement,
    framework_coverage_percent,
)

_FRAMEWORK_SUBTITLE: dict[str, str] = {
    "eu_ai_act": "AI High-Risk Governance",
    "iso_42001": "AIMS",
    "iso_27001": "ISMS",
    "iso_27701": "PIMS / Privacy",
    "nis2": "Cyber-Resilience",
    "dsgvo": "Datenschutz",
}


def build_cross_regulation_summary(
    session: Session,
    tenant_id: str,
) -> CrossRegulationSummaryResponse:
    repo = CrossRegulationRepository(session)
    fw_list = repo.list_frameworks()
    reqs = repo.list_requirements()
    links_by_req = repo.map_requirement_links_for_tenant(tenant_id)

    reqs_by_fw: dict[int, list[int]] = defaultdict(list)
    for r in reqs:
        reqs_by_fw[r.framework_id].append(r.id)

    summaries: list[CrossRegFrameworkSummary] = []
    for fw in fw_list:
        rids = reqs_by_fw.get(fw.id, [])
        total = len(rids)
        covered = 0
        partial = 0
        planned_only = 0
        for rid in rids:
            levels = links_by_req.get(rid, [])
            st = best_coverage_levels_for_requirement(levels)
            if st in ("full", "partial"):
                covered += 1
            if st == "partial":
                partial += 1
            if st == "planned_only":
                planned_only += 1
        gap = total - covered
        pct = framework_coverage_percent(total=total, covered=covered)
        summaries.append(
            CrossRegFrameworkSummary(
                framework_key=fw.key,
                name=fw.name,
                subtitle=_FRAMEWORK_SUBTITLE.get(fw.key, ""),
                total_requirements=total,
                covered_requirements=covered,
                gap_count=gap,
                coverage_percent=pct,
                partial_count=partial,
                planned_only_count=planned_only,
            )
        )

    return CrossRegulationSummaryResponse(tenant_id=tenant_id, frameworks=summaries)


def list_regulatory_frameworks(session: Session) -> list[RegulatoryFrameworkOut]:
    repo = CrossRegulationRepository(session)
    return [
        RegulatoryFrameworkOut(
            id=f.id,
            key=f.key,
            name=f.name,
            description=f.description,
        )
        for f in repo.list_frameworks()
    ]


def _related_keys_for_requirements(
    session: Session,
    requirement_ids: Iterable[int],
) -> dict[int, set[str]]:
    repo = CrossRegulationRepository(session)
    req_fw_key = repo.framework_key_by_requirement_id()
    neighbors = repo.requirement_relation_neighbors(requirement_ids)
    out: dict[int, set[str]] = {}
    for rid in requirement_ids:
        keys: set[str] = set()
        own = req_fw_key.get(rid)
        if own:
            keys.add(own)
        for n in neighbors.get(rid, ()):
            k = req_fw_key.get(n)
            if k:
                keys.add(k)
        out[rid] = keys
    return out


def list_regulatory_requirement_rows(
    session: Session,
    tenant_id: str,
    *,
    framework_key: str | None = None,
) -> list[RegulatoryRequirementOut]:
    repo = CrossRegulationRepository(session)
    fw_by_id = {f.id: f for f in repo.list_frameworks()}
    reqs = repo.list_requirements(framework_key=framework_key)
    if not reqs:
        return []

    links_by_req = repo.map_requirement_links_for_tenant(tenant_id)
    rids = [r.id for r in reqs]
    related = _related_keys_for_requirements(session, rids)

    control_ids_all = repo.list_control_ids_for_tenant(tenant_id)

    req_to_controls: dict[int, list[tuple[str, str]]] = defaultdict(list)
    if control_ids_all:
        link = ComplianceRequirementControlLinkDB
        ctrl = ComplianceControlDB
        q = (
            select(link.requirement_id, ctrl.id, ctrl.name)
            .join(ctrl, ctrl.id == link.control_id)
            .where(
                link.control_id.in_(control_ids_all),
                ctrl.tenant_id == tenant_id,
            )
        )
        for rid, cid, cname in session.execute(q):
            req_to_controls[int(rid)].append((str(cid), str(cname)))

    rows: list[RegulatoryRequirementOut] = []
    for r in reqs:
        fw = fw_by_id.get(r.framework_id)
        if fw is None:
            continue
        fw_key = fw.key
        fw_name = fw.name
        levels = links_by_req.get(r.id, [])
        st = best_coverage_levels_for_requirement(levels)
        ctrls = req_to_controls.get(r.id, [])
        names = [n for _, n in ctrls[:2]]
        rows.append(
            RegulatoryRequirementOut(
                id=r.id,
                framework_key=fw_key,
                framework_name=fw_name,
                code=r.code,
                title=r.title,
                description=r.description,
                requirement_type=r.requirement_type,
                criticality=r.criticality,
                coverage_status=st,
                linked_control_count=len(ctrls),
                primary_control_names=names,
                related_framework_keys=sorted(related.get(r.id, {fw_key})),
            )
        )
    return rows


def list_regulatory_controls(session: Session, tenant_id: str) -> list[RegulatoryControlOut]:
    repo = CrossRegulationRepository(session)
    controls = repo.list_controls(tenant_id)
    if not controls:
        return []

    cids = [c.id for c in controls]
    link = ComplianceRequirementControlLinkDB
    reqt = ComplianceRequirementDB
    fw = ComplianceFrameworkDB
    q = (
        select(link.control_id, reqt.id, fw.key)
        .join(reqt, reqt.id == link.requirement_id)
        .join(fw, fw.id == reqt.framework_id)
        .where(link.control_id.in_(cids))
    )
    ctrl_reqs: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for cid, rid, fk in session.execute(q):
        ctrl_reqs[str(cid)].append((int(rid), str(fk)))

    out: list[RegulatoryControlOut] = []
    for c in controls:
        pairs = ctrl_reqs.get(c.id, [])
        fkeys = {fk for _, fk in pairs}
        out.append(
            RegulatoryControlOut(
                id=c.id,
                name=c.name,
                description=c.description,
                control_type=c.control_type,
                owner_role=c.owner_role,
                status=c.status,
                requirement_count=len(pairs),
                framework_count=len(fkeys),
                framework_keys=sorted(fkeys),
            )
        )
    return out


def get_requirement_controls_detail(
    session: Session,
    tenant_id: str,
    requirement_id: int,
) -> RequirementControlsDetailResponse | None:
    repo = CrossRegulationRepository(session)
    req = repo.get_requirement(requirement_id)
    if req is None:
        return None

    fw = session.scalar(
        select(ComplianceFrameworkDB).where(ComplianceFrameworkDB.id == req.framework_id)
    )
    if fw is None:
        return None

    links_raw = repo.map_links_detail_for_requirement(tenant_id, requirement_id)
    levels = [link.coverage_level for link, _ in links_raw]
    st = best_coverage_levels_for_requirement(levels)

    ctrl_ids = [ctrl.id for _, ctrl in links_raw]
    ai_map = repo.ai_systems_for_controls(tenant_id, ctrl_ids)
    pol_map = repo.policies_for_controls(tenant_id, ctrl_ids)
    act_map = repo.actions_for_controls(tenant_id, ctrl_ids)

    related = _related_keys_for_requirements(session, [requirement_id])

    req_out = RegulatoryRequirementOut(
        id=req.id,
        framework_key=fw.key,
        framework_name=fw.name,
        code=req.code,
        title=req.title,
        description=req.description,
        requirement_type=req.requirement_type,
        criticality=req.criticality,
        coverage_status=st,
        linked_control_count=len(links_raw),
        primary_control_names=[c.name for _, c in links_raw[:2]],
        related_framework_keys=sorted(related.get(req.id, {fw.key})),
    )

    details: list[RequirementControlLinkDetail] = []
    for link, ctrl in links_raw:
        cid = ctrl.id
        details.append(
            RequirementControlLinkDetail(
                link_id=link.id,
                control_id=cid,
                control_name=ctrl.name,
                coverage_level=link.coverage_level,
                control_status=ctrl.status,
                owner_role=ctrl.owner_role,
                ai_system_ids=ai_map.get(cid, []),
                policy_ids=pol_map.get(cid, []),
                action_ids=act_map.get(cid, []),
            )
        )

    return RequirementControlsDetailResponse(requirement=req_out, links=details)


def list_ai_system_regulatory_hints(
    session: Session,
    tenant_id: str,
    ai_system_id: str,
) -> list[AISystemRegulatoryHintOut]:
    repo = CrossRegulationRepository(session)
    rids = repo.requirements_for_ai_system(tenant_id, ai_system_id)
    if not rids:
        return []

    id_to_key = repo.framework_key_by_requirement_id()
    hints: list[AISystemRegulatoryHintOut] = []

    link = ComplianceRequirementControlLinkDB
    ctrl = ComplianceControlDB
    cas = ComplianceControlAISystemDB

    for rid in rids:
        req = repo.get_requirement(rid)
        if req is None:
            continue
        q = (
            select(ctrl.name)
            .join(link, link.control_id == ctrl.id)
            .join(cas, cas.control_id == ctrl.id)
            .where(
                link.requirement_id == rid,
                ctrl.tenant_id == tenant_id,
                cas.tenant_id == tenant_id,
                cas.ai_system_id == ai_system_id,
            )
            .limit(1)
        )
        via = session.scalars(q).first()
        hints.append(
            AISystemRegulatoryHintOut(
                requirement_id=rid,
                code=req.code,
                title=req.title,
                framework_key=id_to_key.get(rid, ""),
                via_control_name=str(via or "Control"),
            )
        )
    return hints


__all__ = [
    "build_cross_regulation_summary",
    "get_requirement_controls_detail",
    "list_ai_system_regulatory_hints",
    "list_regulatory_controls",
    "list_regulatory_frameworks",
    "list_regulatory_requirement_rows",
    "framework_coverage_percent",
    "best_coverage_levels_for_requirement",
]
