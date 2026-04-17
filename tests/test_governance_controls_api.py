"""Unified governance controls API (tenant-scoped)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers(tenant_id: str = "board-kpi-tenant") -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
    }


def test_governance_controls_suggestions_ok() -> None:
    r = client.get("/api/v1/governance/controls/suggestions", headers=_headers())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_governance_controls_crud_flow() -> None:
    h = _headers()
    create = client.post(
        "/api/v1/governance/controls",
        headers=h,
        json={
            "title": "Test-Control Unified Layer",
            "description": "pytest",
            "status": "in_progress",
            "owner": "owner@example.com",
            "framework_tags": ["NIS2", "ISO_27001"],
            "framework_mappings": [
                {"framework": "NIS2", "clause_ref": "Art. 21", "mapping_note": "t"},
            ],
        },
    )
    assert create.status_code == 201, create.text
    cid = create.json()["id"]

    got = client.get(f"/api/v1/governance/controls/{cid}", headers=h)
    assert got.status_code == 200
    assert got.json()["title"] == "Test-Control Unified Layer"

    lst = client.get("/api/v1/governance/controls", headers=h)
    assert lst.status_code == 200
    assert any(row["id"] == cid for row in lst.json())

    summ = client.get("/api/v1/governance/controls/dashboard/summary", headers=h)
    assert summ.status_code == 200
    assert summ.json()["total_controls"] >= 1

    ev = client.post(
        f"/api/v1/governance/controls/{cid}/evidence",
        headers=h,
        json={"title": "Policy PDF", "source_type": "manual"},
    )
    assert ev.status_code == 201, ev.text

    patch = client.patch(
        f"/api/v1/governance/controls/{cid}",
        headers=h,
        json={"status": "implemented"},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "implemented"

    ev_list = client.get(f"/api/v1/governance/controls/{cid}/evidence", headers=h)
    assert ev_list.status_code == 200
    assert isinstance(ev_list.json(), list)
    assert len(ev_list.json()) >= 1

    hist = client.get(f"/api/v1/governance/controls/{cid}/status-history", headers=h)
    assert hist.status_code == 200
    assert isinstance(hist.json(), list)

    lst2 = client.get("/api/v1/governance/controls?offset=0&limit=10", headers=h)
    assert lst2.status_code == 200
    assert lst2.headers.get("X-Total-Count") is not None
    assert int(lst2.headers["X-Total-Count"]) >= 1

    export_r = client.get("/api/v1/governance/controls/export", headers=h)
    assert export_r.status_code == 200
    assert "text/csv" in (export_r.headers.get("content-type") or "")


def test_governance_controls_materialize_idempotent() -> None:
    h = _headers()
    key = "pytest_suggestion_stub"
    create = client.post(
        "/api/v1/governance/controls",
        headers=h,
        json={
            "title": "Pre-materialized",
            "status": "not_started",
            "framework_tags": ["NIS2"],
            "framework_mappings": [],
            "source_inputs": {"materialized_from_suggestion": key},
        },
    )
    assert create.status_code == 201, create.text
    cid = create.json()["id"]

    mat = client.post(
        "/api/v1/governance/controls/from-suggestion",
        headers=h,
        json={"suggestion_key": key},
    )
    assert mat.status_code == 200
    assert mat.json()["id"] == cid


def test_governance_controls_from_suggestion_unknown() -> None:
    h = _headers()
    r = client.post(
        "/api/v1/governance/controls/from-suggestion",
        headers=h,
        json={"suggestion_key": "definitely_unknown_key_xyz"},
    )
    assert r.status_code == 404
