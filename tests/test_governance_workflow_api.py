"""Governance Workflow Orchestration API (tenant-scoped, async DB)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE = "/api/v1/governance/workflows"


def _headers(tenant_id: str = "board-kpi-tenant") -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
    }


def test_workflow_dashboard_shape() -> None:
    r = client.get(BASE, headers=_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert "kpis" in body
    assert "rule_bundle_version" in body
    assert "recent_runs" in body
    assert "templates" in body
    k = body["kpis"]
    assert set(k.keys()) >= {
        "open_tasks",
        "overdue_tasks",
        "escalated_tasks",
        "notifications_queued",
        "workflow_events_24h",
    }


def test_workflow_run_and_test_notification() -> None:
    h = _headers()
    run = client.post(f"{BASE}/run", headers=h, json={"rule_profile": "default"})
    assert run.status_code == 201, run.text
    j = run.json()
    assert j["status"] == "completed"
    assert "run_id" in j
    n = client.post(
        f"{BASE}/notifications/test",
        headers=h,
        json={"channel": "test", "title": "pytest", "body": "hi"},
    )
    assert n.status_code == 201, n.text
    assert n.json()["result"] == "ok"


def test_tasks_list_two_tenants_ok() -> None:
    a = client.get(f"{BASE}/tasks", headers=_headers("board-kpi-tenant"))
    b = client.get(f"{BASE}/tasks", headers=_headers("demo-seed-tenant-1"))
    assert a.status_code == 200 and b.status_code == 200
    assert isinstance(a.json(), list) and isinstance(b.json(), list)


def test_invalid_rule_profile() -> None:
    r = client.post(
        f"{BASE}/run", headers=_headers(), json={"rule_profile": "nonexistent"}
    )
    assert r.status_code == 400
