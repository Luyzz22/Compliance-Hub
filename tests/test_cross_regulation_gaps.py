"""Unit-Tests: Cross-Regulation-Gap-Aggregation (ohne LLM)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.models_db import (
    ComplianceControlDB,
    ComplianceFrameworkDB,
    ComplianceRequirementControlLinkDB,
    ComplianceRequirementDB,
    TenantDB,
)
from app.services.cross_regulation_gaps import compute_cross_regulation_gaps


def _eu_art9_id(session: Session) -> int:
    stmt_fw = select(ComplianceFrameworkDB).where(ComplianceFrameworkDB.key == "eu_ai_act")
    fw = session.scalars(stmt_fw).one()
    req = session.scalars(
        select(ComplianceRequirementDB).where(
            ComplianceRequirementDB.framework_id == fw.id,
            ComplianceRequirementDB.code == "Art.9",
        )
    ).one()
    return int(req.id)


def test_compute_gaps_lists_partial_and_empty_links(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD", "true")
    tid = f"gap-ut-{uuid.uuid4().hex[:10]}"
    with Session(engine) as s:
        s.add(
            TenantDB(
                id=tid,
                display_name="UT",
                industry="professional_services",
                country="DE",
            )
        )
        s.commit()

        rid = _eu_art9_id(s)
        cid = str(uuid.uuid4())
        s.add(
            ComplianceControlDB(
                id=cid,
                tenant_id=tid,
                name="Teil-Control",
                description=None,
                control_type="process",
                owner_role="CISO",
                status="planned",
            )
        )
        s.add(
            ComplianceRequirementControlLinkDB(
                requirement_id=rid,
                control_id=cid,
                coverage_level="partial",
            )
        )
        s.commit()

        payload = compute_cross_regulation_gaps(s, tid)
        assert payload.tenant_id == tid
        assert payload.tenant_industry_hint == "professional_services"
        gap_ids = {g.requirement_id for g in payload.gaps}
        assert rid in gap_ids
        g_art9 = next(g for g in payload.gaps if g.requirement_id == rid)
        assert g_art9.coverage_status == "partial"
        assert len(g_art9.linked_controls) == 1
        assert g_art9.linked_controls[0].name == "Teil-Control"

        fw_keys = {c.framework_key for c in payload.coverage}
        assert "eu_ai_act" in fw_keys


def test_compute_gaps_focus_framework_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD", "true")
    tid = f"gap-focus-{uuid.uuid4().hex[:10]}"
    with Session(engine) as s:
        s.add(TenantDB(id=tid, display_name="UT", industry="IT", country="DE"))
        s.commit()
        p = compute_cross_regulation_gaps(s, tid, focus_framework_keys=["nis2"])
        assert all(g.framework_key == "nis2" for g in p.gaps)
        assert all(f.framework_key == "nis2" for f in p.coverage)
