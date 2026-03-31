"""
Smoke-Test: Demo-Seed + zentrale GETs für Board-/Advisor-Walkthrough (CI / Pre-Demo).

Prüft nicht jedes UI-Feld, sondern: Seed ok, Readiness, Governance Maturity (GAI+OAMI),
Board-Reports, Hochrisiko-Systeme vorhanden.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import get_settings

TENANT = "demo-smoke-e2e"
DEMO_KEY = "demo-seed-key"
TENANT_KEY = "board-kpi-key"


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _seed(client: TestClient) -> None:
    r = client.post(
        "/api/v1/demo/tenants/seed",
        headers={"x-api-key": DEMO_KEY},
        json={"template_key": "industrial_sme", "tenant_id": TENANT},
    )
    assert r.status_code in (200, 409), r.text


def _th() -> dict[str, str]:
    return {"x-api-key": TENANT_KEY, "x-tenant-id": TENANT}


def test_demo_walkthrough_smoke_seed_and_core_apis(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_READINESS_SCORE", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT", "true")
    get_settings.cache_clear()

    _seed(client)

    r_rs = client.get(f"/api/v1/tenants/{TENANT}/readiness-score", headers=_th())
    assert r_rs.status_code == 200, r_rs.text
    rs = r_rs.json()
    assert 0 <= int(rs.get("score", -1)) <= 100
    assert rs.get("level") in ("basic", "managed", "embedded")

    r_gm = client.get(f"/api/v1/tenants/{TENANT}/governance-maturity", headers=_th())
    assert r_gm.status_code == 200, r_gm.text
    gm = r_gm.json()
    assert gm["tenant_id"] == TENANT
    gai = gm["governance_activity"]
    assert 0 <= int(gai["index"]) <= 100
    assert gai["level"] in ("low", "medium", "high")
    oam = gm["operational_ai_monitoring"]
    assert oam["status"] in ("active", "not_configured")
    if oam["status"] == "active":
        assert oam["index"] is not None
        assert 0 <= int(oam["index"]) <= 100

    r_br = client.get(f"/api/v1/tenants/{TENANT}/board/ai-compliance-reports", headers=_th())
    assert r_br.status_code == 200, r_br.text
    reports = r_br.json()
    assert isinstance(reports, list)
    assert len(reports) >= 1

    r_ai = client.get("/api/v1/ai-systems", headers=_th())
    assert r_ai.status_code == 200, r_ai.text
    systems = r_ai.json()
    assert isinstance(systems, list)
    assert len(systems) >= 1
    high = [s for s in systems if str(s.get("risk_level", "")).lower() == "high"]
    assert len(high) >= 1
