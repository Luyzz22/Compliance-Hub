"""Remediation & action tracking API (tenant-scoped, async DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE = "/api/v1/governance/remediation-actions"


def _headers(tenant_id: str = "board-kpi-tenant") -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
    }


def test_remediation_list_summary_shape() -> None:
    r = client.get(BASE, headers=_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert "items" in body and "summary" in body
    s = body["summary"]
    assert set(s.keys()) >= {
        "open_actions",
        "overdue_actions",
        "blocked_actions",
        "due_this_week",
    }


def test_remediation_crud_comment_generate_flow() -> None:
    h = _headers()
    c = client.post(
        "/api/v1/governance/controls",
        headers=h,
        json={
            "title": "Remediation link fixture",
            "description": "pytest",
            "status": "not_started",
            "framework_tags": ["EU_AI_ACT"],
            "framework_mappings": [],
        },
    )
    assert c.status_code == 201, c.text
    cid = c.json()["id"]

    create = client.post(
        BASE,
        headers=h,
        json={
            "title": "Manuelle Maßnahme (pytest)",
            "description": "Scope test",
            "priority": "high",
            "category": "manual",
            "links": [{"entity_type": "governance_control", "entity_id": cid}],
        },
    )
    assert create.status_code == 201, create.text
    aid = create.json()["id"]
    assert create.json()["status"] == "open"
    assert create.json()["links"][0]["entity_id"] == cid

    got = client.get(f"{BASE}/{aid}", headers=h)
    assert got.status_code == 200
    assert got.json()["title"] == "Manuelle Maßnahme (pytest)"
    assert len(got.json()["status_history"]) >= 1

    patch = client.patch(
        f"{BASE}/{aid}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "in_progress"

    cm = client.post(
        f"{BASE}/{aid}/comments",
        headers=h,
        json={"body": "Kommentar pytest"},
    )
    assert cm.status_code == 201, cm.text

    detail = client.get(f"{BASE}/{aid}", headers=h)
    assert detail.status_code == 200
    assert any(x["body"] == "Kommentar pytest" for x in detail.json()["comments"])

    gen = client.post(f"{BASE}/generate", headers=h)
    assert gen.status_code == 200, gen.text
    assert "created_count" in gen.json()
    assert "rule_keys_touched" in gen.json()


def test_remediation_accepted_risk_requires_note() -> None:
    h = _headers()
    create = client.post(
        BASE,
        headers=h,
        json={
            "title": "Risk acceptance fixture",
            "priority": "low",
            "category": "manual",
            "links": [],
        },
    )
    assert create.status_code == 201
    aid = create.json()["id"]

    bad = client.patch(
        f"{BASE}/{aid}",
        headers=h,
        json={"status": "accepted_risk"},
    )
    assert bad.status_code == 400

    ok = client.patch(
        f"{BASE}/{aid}",
        headers=h,
        json={"status": "accepted_risk", "deferred_note": "Budget / Phase 2"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "accepted_risk"


def test_remediation_invalid_control_link_400() -> None:
    h = _headers()
    r = client.post(
        BASE,
        headers=h,
        json={
            "title": "Bad link",
            "priority": "medium",
            "category": "manual",
            "links": [
                {
                    "entity_type": "governance_control",
                    "entity_id": "00000000-0000-0000-0000-000000000099",
                }
            ],
        },
    )
    assert r.status_code == 400


def test_remediation_tenant_isolation_on_detail() -> None:
    h = _headers("board-kpi-tenant")
    create = client.post(
        BASE,
        headers=h,
        json={
            "title": "Tenant A only",
            "priority": "medium",
            "category": "manual",
            "links": [],
        },
    )
    assert create.status_code == 201
    aid = create.json()["id"]

    other = _headers("other-remediation-tenant")
    r = client.get(f"{BASE}/{aid}", headers=other)
    assert r.status_code == 404
