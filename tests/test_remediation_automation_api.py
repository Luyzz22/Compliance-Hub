"""Remediation automation & escalation API."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE = "/api/v1/governance/remediation-actions"


def _headers(tenant_id: str = "board-kpi-tenant") -> dict[str, str]:
    return {
        "x-api-key": "board-kpi-key",
        "x-tenant-id": tenant_id,
    }


def test_automation_summary_shape() -> None:
    r = client.get(f"{BASE}/automation/summary", headers=_headers())
    assert r.status_code == 200, r.text
    b = r.json()
    for k in (
        "overdue_actions",
        "severe_escalations_open",
        "management_escalations_open",
        "reminders_due_today",
        "auto_generated_actions_7d",
    ):
        assert k in b


def test_automation_run_and_escalations_list() -> None:
    h = _headers()
    due = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    c = client.post(
        BASE,
        headers=h,
        json={
            "title": "Automation overdue fixture",
            "priority": "medium",
            "category": "manual",
            "due_at_utc": due,
            "links": [],
        },
    )
    assert c.status_code == 201, c.text
    aid = c.json()["id"]

    run = client.post(f"{BASE}/automation/run", headers=h)
    assert run.status_code == 200, run.text
    body = run.json()
    assert "run_id" in body
    assert body.get("escalations_created", 0) >= 1

    esc = client.get(f"{BASE}/escalations?status=open", headers=h)
    assert esc.status_code == 200
    rows = esc.json()["items"]
    match = next(x for x in rows if x["action_id"] == aid and x["severity"] == "overdue")
    assert "action_title" in match
    assert match.get("action_title") == "Automation overdue fixture"

    ack = client.post(f"{BASE}/{aid}/acknowledge-escalation", headers=h)
    assert ack.status_code == 200, ack.text
    assert ack.json()["acknowledged"] >= 1

    esc2 = client.get(f"{BASE}/escalations?status=open", headers=h)
    assert not any(x["action_id"] == aid for x in esc2.json()["items"])


def test_acknowledge_idempotent_when_no_open_escalations() -> None:
    h = _headers()
    r = client.post(
        f"{BASE}/{uuid.uuid4()}/acknowledge-escalation",
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["acknowledged"] == 0
    assert body["escalation_ids"] == []


def test_automation_tenant_isolation() -> None:
    h = _headers("tenant-a-auto")
    client.post(f"{BASE}/automation/run", headers=h)
    other = _headers("tenant-b-auto")
    r = client.get(f"{BASE}/escalations", headers=other)
    assert r.status_code == 200
    assert r.json()["items"] == []
