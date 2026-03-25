"""API-Tests Cross-Regulation / Regelwerksgraph."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import engine
from app.main import app
from app.models_db import (
    ComplianceControlDB,
    ComplianceFrameworkDB,
    ComplianceRequirementControlLinkDB,
    ComplianceRequirementDB,
)
from tests.conftest import _headers

client = TestClient(app)


def _eu_art9_requirement_id(session: Session) -> int:
    stmt = select(ComplianceFrameworkDB).where(ComplianceFrameworkDB.key == "eu_ai_act")
    fw = session.scalars(stmt).one()
    req = session.scalars(
        select(ComplianceRequirementDB).where(
            ComplianceRequirementDB.framework_id == fw.id,
            ComplianceRequirementDB.code == "Art.9",
        )
    ).one()
    return int(req.id)


def test_cross_regulation_forbidden_when_feature_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD", "false")
    h = _headers()
    tid = h["x-tenant-id"]
    r = client.get(f"/api/v1/tenants/{tid}/compliance/cross-regulation/summary", headers=h)
    assert r.status_code == 403


def test_cross_regulation_summary_aggregates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD", "true")
    tid = f"cr-tenant-{uuid.uuid4().hex[:10]}"
    h = {"x-api-key": "board-kpi-key", "x-tenant-id": tid}

    r = client.get(f"/api/v1/tenants/{tid}/compliance/cross-regulation/summary", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == tid
    fws = {x["framework_key"]: x for x in body["frameworks"]}
    assert "eu_ai_act" in fws
    assert fws["eu_ai_act"]["total_requirements"] >= 7
    assert fws["eu_ai_act"]["covered_requirements"] == 0
    assert fws["eu_ai_act"]["gap_count"] == fws["eu_ai_act"]["total_requirements"]

    rid = None
    with Session(engine) as s:
        rid = _eu_art9_requirement_id(s)
        cid = str(uuid.uuid4())
        s.add(
            ComplianceControlDB(
                id=cid,
                tenant_id=tid,
                name="KI-Risikomanagement-Prozess",
                description="Map once",
                control_type="process",
                owner_role="CISO",
                status="implemented",
            )
        )
        s.add(
            ComplianceRequirementControlLinkDB(
                requirement_id=rid,
                control_id=cid,
                coverage_level="full",
            )
        )
        s.commit()

    r2 = client.get(f"/api/v1/tenants/{tid}/compliance/cross-regulation/summary", headers=h)
    assert r2.status_code == 200
    fws2 = {x["framework_key"]: x for x in r2.json()["frameworks"]}
    assert fws2["eu_ai_act"]["covered_requirements"] >= 1
    eu = fws2["eu_ai_act"]
    assert eu["gap_count"] == eu["total_requirements"] - eu["covered_requirements"]

    r3 = client.get(
        f"/api/v1/tenants/{tid}/compliance/regulatory-requirements?framework=eu_ai_act",
        headers=h,
    )
    assert r3.status_code == 200
    rows = r3.json()
    art9 = next(x for x in rows if x["code"] == "Art.9")
    assert art9["coverage_status"] in ("full", "partial")
    assert art9["linked_control_count"] >= 1

    r4 = client.get(
        f"/api/v1/tenants/{tid}/compliance/regulatory-requirements/{rid}/controls",
        headers=h,
    )
    assert r4.status_code == 200
    assert r4.json()["requirement"]["code"] == "Art.9"
    assert len(r4.json()["links"]) >= 1


def test_cross_regulation_tenant_path_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD", "true")
    h = _headers()
    r = client.get("/api/v1/tenants/other-tenant/compliance/cross-regulation/summary", headers=h)
    assert r.status_code == 403
