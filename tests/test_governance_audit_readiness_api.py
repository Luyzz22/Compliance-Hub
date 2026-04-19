"""Governance audit readiness API (tenant-scoped)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers(tenant_id: str = "board-kpi-tenant") -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
    }


def test_audit_readiness_happy_path() -> None:
    h = _headers()
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    c = client.post(
        "/api/v1/governance/controls",
        headers=h,
        json={
            "title": "Audit readiness fixture control",
            "status": "implemented",
            "owner": "ciso@example.com",
            "next_review_at": future,
            "framework_tags": ["NIS2"],
            "framework_mappings": [
                {"framework": "NIS2", "clause_ref": "Art. 21", "mapping_note": "t"},
            ],
        },
    )
    assert c.status_code == 201, c.text
    cid = c.json()["id"]
    for st in ("policy", "incident_evidence", "manual"):
        ev = client.post(
            f"/api/v1/governance/controls/{cid}/evidence",
            headers=h,
            json={"title": f"Evidence {st}", "source_type": st},
        )
        assert ev.status_code == 201, ev.text

    a = client.post(
        "/api/v1/governance/audits",
        headers=h,
        json={
            "title": "FY26 NIS2 readiness",
            "description": "pytest",
            "framework_tags": ["NIS2"],
            "control_ids": [cid],
        },
    )
    assert a.status_code == 201, a.text
    aid = a.json()["id"]

    r = client.get(f"/api/v1/governance/audits/{aid}/readiness", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["controls_total"] == 1
    assert body["controls_ready"] == 1
    assert body["overall_readiness_pct"] == 100.0

    rows = client.get(f"/api/v1/governance/audits/{aid}/controls", headers=h)
    assert rows.status_code == 200
    assert rows.json()[0]["is_ready"] is True

    tr = client.get(f"/api/v1/governance/audits/{aid}/trail", headers=h)
    assert tr.status_code == 200
    assert len(tr.json()) >= 1


def test_audit_attach_control() -> None:
    h = _headers()
    c = client.post(
        "/api/v1/governance/controls",
        headers=h,
        json={
            "title": "Loose control for attach",
            "status": "not_started",
            "framework_tags": ["ISO_27001"],
            "framework_mappings": [],
        },
    )
    assert c.status_code == 201
    cid = c.json()["id"]
    a = client.post(
        "/api/v1/governance/audits",
        headers=h,
        json={"title": "ISO audit", "framework_tags": ["ISO_27701"], "control_ids": []},
    )
    assert a.status_code == 201
    aid = a.json()["id"]
    att = client.post(
        f"/api/v1/governance/audits/{aid}/controls/{cid}/attach",
        headers=h,
    )
    assert att.status_code == 200
    assert cid in att.json()["control_ids"]
