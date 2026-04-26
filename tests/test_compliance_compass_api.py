"""Compliance Compass API — Shape & Mandanten-Isolation."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COMPASS = "/api/v1/governance/compass/snapshot"


def _h(tid: str) -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tid}


def test_compass_snapshot_200_and_shape() -> None:
    r = client.get(COMPASS, headers=_h("board-kpi-tenant"))
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["tenant_id"] == "board-kpi-tenant"
    for k in (
        "as_of_utc",
        "model_version",
        "fusion_index_0_100",
        "confidence_0_100",
        "posture",
        "narrative_de",
        "pillars",
        "provenance",
        "privacy_de",
    ):
        assert k in j
    assert 0 <= j["fusion_index_0_100"] <= 100
    assert 0 <= j["confidence_0_100"] <= 100
    assert isinstance(j["pillars"], list) and len(j["pillars"]) == 4
    prov = j["provenance"]
    for k2 in (
        "readiness_score",
        "workflow_open_or_active",
        "workflow_overdue",
        "workflow_escalated",
        "workflow_events_24h",
    ):
        assert k2 in prov


def test_compass_tenant_a_ne_b() -> None:
    a = client.get(COMPASS, headers=_h("board-kpi-tenant")).json()
    b = client.get(COMPASS, headers=_h("demo-seed-tenant-1")).json()
    assert a["tenant_id"] != b["tenant_id"]


def test_compass_401_or_400_without_auth() -> None:
    r = client.get(COMPASS, headers={})
    assert r.status_code in (400, 401)
