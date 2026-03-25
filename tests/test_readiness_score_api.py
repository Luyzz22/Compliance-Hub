"""API: Readiness Score (Tenant, Berater-Proxy, Feature-Flag)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.repositories.advisor_tenants import AdvisorTenantRepository

client = TestClient(app)

ADV_RD = "advisor-readiness@example.com"
T_ADV_LINKED = "adv-readiness-tenant-linked"
T_ADV_OTHER = "adv-readiness-tenant-other"


def _headers(tenant_id: str) -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
    }


def test_readiness_score_forbidden_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_READINESS_SCORE", "false")
    tid = "tenant-readiness-off-1"
    r = client.get(f"/api/v1/tenants/{tid}/readiness-score", headers=_headers(tid))
    assert r.status_code == 403
    assert "readiness_score" in r.json()["detail"]


def test_readiness_score_200_structure() -> None:
    tid = "tenant-readiness-open-1"
    r = client.get(f"/api/v1/tenants/{tid}/readiness-score", headers=_headers(tid))
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == tid
    assert 0 <= body["score"] <= 100
    assert body["level"] in ("basic", "managed", "embedded")
    assert "interpretation" in body
    for key in ("setup", "coverage", "kpi", "gaps", "reporting"):
        assert key in body["dimensions"]
        dim = body["dimensions"][key]
        assert "normalized" in dim and "score_0_100" in dim


def test_readiness_score_tenant_mismatch() -> None:
    tid = "tenant-readiness-a"
    r = client.get("/api/v1/tenants/other/readiness-score", headers=_headers(tid))
    assert r.status_code == 403


@pytest.fixture
def advisor_readiness_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ADVISOR_IDS", ADV_RD)


def _adv_headers() -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-advisor-id": ADV_RD}


def _seed_advisor_readiness_link() -> None:
    s = SessionLocal()
    try:
        AdvisorTenantRepository(s).upsert_link(
            advisor_id=ADV_RD,
            tenant_id=T_ADV_LINKED,
            tenant_display_name="Readiness Mandant GmbH",
            industry="IT",
            country="DE",
        )
    finally:
        s.close()


def test_advisor_readiness_score_forbidden_when_flag_off(
    advisor_readiness_allowlist: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_READINESS_SCORE", "false")
    _seed_advisor_readiness_link()
    r = client.get(
        f"/api/v1/advisors/{ADV_RD}/tenants/{T_ADV_LINKED}/readiness-score",
        headers=_adv_headers(),
    )
    assert r.status_code == 403
    assert "readiness_score" in r.json()["detail"]


def test_advisor_readiness_score_404_when_not_linked(
    advisor_readiness_allowlist: None,
) -> None:
    r = client.get(
        f"/api/v1/advisors/{ADV_RD}/tenants/{T_ADV_OTHER}/readiness-score",
        headers=_adv_headers(),
    )
    assert r.status_code == 404
    assert "not linked" in r.json()["detail"].lower()


def test_advisor_readiness_score_200_same_shape_as_tenant(
    advisor_readiness_allowlist: None,
) -> None:
    _seed_advisor_readiness_link()
    r_adv = client.get(
        f"/api/v1/advisors/{ADV_RD}/tenants/{T_ADV_LINKED}/readiness-score",
        headers=_adv_headers(),
    )
    assert r_adv.status_code == 200
    body_adv = r_adv.json()
    assert body_adv["tenant_id"] == T_ADV_LINKED
    assert 0 <= body_adv["score"] <= 100
    assert body_adv["level"] in ("basic", "managed", "embedded")

    r_tenant = client.get(
        f"/api/v1/tenants/{T_ADV_LINKED}/readiness-score",
        headers=_headers(T_ADV_LINKED),
    )
    assert r_tenant.status_code == 200
    body_t = r_tenant.json()
    assert body_adv["score"] == body_t["score"]
    assert body_adv["level"] == body_t["level"]
    assert body_adv["dimensions"] == body_t["dimensions"]
