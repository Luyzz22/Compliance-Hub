"""Governance Workflow Orchestration API (tenant-scoped, async DB)."""

from __future__ import annotations

import pytest
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
    assert "events_written" in j
    assert isinstance(j["events_written"], int)
    assert j["events_written"] >= 0
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
    r = client.post(f"{BASE}/run", headers=_headers(), json={"rule_profile": "nonexistent"})
    assert r.status_code == 400


def test_task_patch_invalid_status_422() -> None:
    h = _headers()
    client.post(f"{BASE}/run", headers=h, json={"rule_profile": "default"})
    lr = client.get(f"{BASE}/tasks", headers=h)
    assert lr.status_code == 200
    items = lr.json()
    if not items:
        pytest.skip("no workflow tasks in fixture DB for this tenant")
    tid = items[0]["id"]
    p = client.patch(
        f"{BASE}/tasks/{tid}",
        headers=h,
        json={"status": "not_a_valid_status"},
    )
    assert p.status_code == 422, p.text


def test_task_clear_assignee_explicit_null() -> None:
    h = _headers()
    client.post(f"{BASE}/run", headers=h, json={"rule_profile": "default"})
    lr = client.get(f"{BASE}/tasks", headers=h)
    assert lr.status_code == 200
    items = lr.json()
    if not items:
        pytest.skip("no workflow tasks in fixture DB for this tenant")
    tid = items[0]["id"]
    u1 = client.patch(f"{BASE}/tasks/{tid}", headers=h, json={"assignee_user_id": "test-owner-1"})
    assert u1.status_code == 200, u1.text
    d = client.get(f"{BASE}/tasks/{tid}", headers=h)
    assert d.json()["assignee_user_id"] == "test-owner-1"
    u2 = client.patch(f"{BASE}/tasks/{tid}", headers=h, json={"assignee_user_id": None})
    assert u2.status_code == 200, u2.text
    d2 = client.get(f"{BASE}/tasks/{tid}", headers=h)
    assert d2.json()["assignee_user_id"] is None
