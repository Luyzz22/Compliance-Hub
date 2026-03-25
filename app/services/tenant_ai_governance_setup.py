"""Merge-Logik und Fortschritt für den AI-Governance-Setup-Wizard."""

from __future__ import annotations

import copy
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models_db import AiComplianceBoardReportDB, AiSystemKpiValueDB, AISystemTable
from app.tenant_ai_governance_setup_models import (
    TenantAIGovernanceSetupPatch,
    TenantAIGovernanceSetupResponse,
)


def _default_payload() -> dict[str, Any]:
    return {
        "tenant_kind": None,
        "compliance_scopes": [],
        "governance_roles": {},
        "active_frameworks": [],
        "steps_marked_complete": [],
        "flags": {
            "gap_assist_previewed": False,
            "board_report_created": False,
        },
    }


def normalize_payload(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = _default_payload()
    if not raw:
        return base
    merged = copy.deepcopy(base)
    for k, v in raw.items():
        if k == "flags" and isinstance(v, dict):
            merged["flags"] = {**merged.get("flags", {}), **v}
        elif k in merged and v is not None:
            merged[k] = copy.deepcopy(v)
    return merged


def apply_setup_patch(base: dict[str, Any], patch: TenantAIGovernanceSetupPatch) -> dict[str, Any]:
    out = copy.deepcopy(base)
    data = patch.model_dump(exclude_unset=True)

    if "mark_steps_complete" in data and data["mark_steps_complete"] is not None:
        cur = set(out.get("steps_marked_complete", []))
        for s in data["mark_steps_complete"]:
            if isinstance(s, int) and 1 <= s <= 6:
                cur.add(s)
        out["steps_marked_complete"] = sorted(cur)
        del data["mark_steps_complete"]

    if "flags" in data and data["flags"] is not None:
        out.setdefault("flags", {}).update(data["flags"])
        del data["flags"]

    for key in ("compliance_scopes", "active_frameworks"):
        if key in data and data[key] is not None:
            out[key] = copy.deepcopy(data[key])
            del data[key]

    if "governance_roles" in data and data["governance_roles"] is not None:
        out.setdefault("governance_roles", {}).update(dict(data["governance_roles"]))
        del data["governance_roles"]

    for key, value in data.items():
        if value is not None:
            out[key] = value

    return out


def _count_systems(session: Session, tenant_id: str) -> int:
    n = session.scalar(
        select(func.count()).select_from(AISystemTable).where(AISystemTable.tenant_id == tenant_id),
    )
    return int(n or 0)


def _count_kpi_values(session: Session, tenant_id: str) -> int:
    n = session.scalar(
        select(func.count())
        .select_from(AiSystemKpiValueDB)
        .where(AiSystemKpiValueDB.tenant_id == tenant_id),
    )
    return int(n or 0)


def _count_board_reports(session: Session, tenant_id: str) -> int:
    n = session.scalar(
        select(func.count())
        .select_from(AiComplianceBoardReportDB)
        .where(AiComplianceBoardReportDB.tenant_id == tenant_id),
    )
    return int(n or 0)


def compute_progress_steps(session: Session, tenant_id: str, payload: dict[str, Any]) -> list[int]:
    inferred: set[int] = set()
    if payload.get("tenant_kind"):
        inferred.add(1)
    if payload.get("active_frameworks"):
        inferred.add(2)
    if _count_systems(session, tenant_id) > 0:
        inferred.add(3)
    if _count_kpi_values(session, tenant_id) > 0:
        inferred.add(4)
    flags = payload.get("flags") or {}
    if flags.get("gap_assist_previewed"):
        inferred.add(5)
    if flags.get("board_report_created") or _count_board_reports(session, tenant_id) > 0:
        inferred.add(6)

    marked = {s for s in payload.get("steps_marked_complete", []) if isinstance(s, int)}
    return sorted(inferred | marked)


def build_setup_response(
    session: Session,
    tenant_id: str,
    payload: dict[str, Any],
) -> TenantAIGovernanceSetupResponse:
    p = normalize_payload(payload)
    progress = compute_progress_steps(session, tenant_id, p)
    return TenantAIGovernanceSetupResponse(
        tenant_id=tenant_id,
        tenant_kind=p.get("tenant_kind"),
        compliance_scopes=list(p.get("compliance_scopes") or []),
        governance_roles=dict(p.get("governance_roles") or {}),
        active_frameworks=list(p.get("active_frameworks") or []),
        steps_marked_complete=list(p.get("steps_marked_complete") or []),
        flags=dict(p.get("flags") or {}),
        progress_steps=progress,
    )
