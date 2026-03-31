"""Cross-Regulation: strukturierte Gap-Liste und Coverage für LLM-Assist (ohne PII)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.cross_regulation_models import (
    CrossRegGapLinkedControlSnapshot,
    CrossRegGapRequirementItem,
    CrossRegulationGapsPayload,
)
from app.repositories.cross_regulation import CrossRegulationRepository
from app.repositories.tenant_registry import TenantRegistryRepository
from app.services.cross_regulation import build_cross_regulation_summary
from app.services.cross_regulation_coverage import best_coverage_levels_for_requirement


def _linked_snapshots(
    session: Session,
    tenant_id: str,
    requirement_id: int,
) -> list[CrossRegGapLinkedControlSnapshot]:
    repo = CrossRegulationRepository(session)
    links_raw = repo.map_links_detail_for_requirement(tenant_id, requirement_id)
    if not links_raw:
        return []
    ctrl_ids = [c.id for _, c in links_raw]
    ai_map = repo.ai_systems_for_controls(tenant_id, ctrl_ids)
    pol_map = repo.policies_for_controls(tenant_id, ctrl_ids)
    act_map = repo.actions_for_controls(tenant_id, ctrl_ids)
    out: list[CrossRegGapLinkedControlSnapshot] = []
    for link, ctrl in links_raw:
        cid = ctrl.id
        out.append(
            CrossRegGapLinkedControlSnapshot(
                control_id=cid,
                name=ctrl.name,
                status=ctrl.status,
                coverage_level=link.coverage_level,
                owner_role=ctrl.owner_role,
                ai_system_ids=sorted(ai_map.get(cid, [])),
                policy_ids=sorted(pol_map.get(cid, [])),
                action_ids=sorted(act_map.get(cid, [])),
            )
        )
    return out


def _is_gap_status(st: str) -> bool:
    return st in ("gap", "partial", "planned_only")


def compute_cross_regulation_gaps(
    session: Session,
    tenant_id: str,
    *,
    focus_framework_keys: list[str] | None = None,
) -> CrossRegulationGapsPayload:
    """
    Sammelt alle Pflichten mit Lücke / Teilabdeckung / nur geplant inkl. Control-Metadaten.

    Keine Beschreibungstexte oder Dokumentinhalte – nur Codes, Titel, Status, IDs.
    """
    summary = build_cross_regulation_summary(session, tenant_id)
    focus = {k.strip() for k in (focus_framework_keys or []) if k and str(k).strip()}
    coverage_rows = (
        [f for f in summary.frameworks if f.framework_key in focus]
        if focus
        else list(summary.frameworks)
    )

    repo = CrossRegulationRepository(session)
    fw_by_id = {f.id: f for f in repo.list_frameworks()}
    reqs = repo.list_requirements()
    links_by_req = repo.map_requirement_links_for_tenant(tenant_id)

    industry_hint: str | None = None
    trow = TenantRegistryRepository(session).get_by_id(tenant_id)
    if trow is not None and trow.industry:
        industry_hint = trow.industry.strip() or None

    gaps: list[CrossRegGapRequirementItem] = []
    for r in reqs:
        fw = fw_by_id.get(r.framework_id)
        if fw is None:
            continue
        if focus and fw.key not in focus:
            continue
        levels = links_by_req.get(r.id, [])
        st = best_coverage_levels_for_requirement(levels)
        if not _is_gap_status(st):
            continue
        snaps = _linked_snapshots(session, tenant_id, r.id)
        gaps.append(
            CrossRegGapRequirementItem(
                requirement_id=r.id,
                framework_key=fw.key,
                code=r.code,
                title=r.title,
                criticality=r.criticality,
                requirement_type=r.requirement_type,
                coverage_status=st,
                linked_controls=snaps,
            )
        )

    return CrossRegulationGapsPayload(
        tenant_id=tenant_id,
        tenant_industry_hint=industry_hint,
        coverage=coverage_rows,
        gaps=gaps,
    )
