from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.compliance_calendar_models import EscalationLevel
from app.main import app
from app.repositories.compliance_deadlines import _compute_escalation

TENANT_A = "cal-test-tenant-a"
TENANT_B = "cal-test-tenant-b"
API_KEY = "test-key"
BASE = "/api/v1/compliance-calendar"


def _headers(tenant: str = TENANT_A) -> dict[str, str]:
    return {"x-api-key": API_KEY, "x-tenant-id": tenant}


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


# ── 1. Create deadline ─────────────────────────────────────────────────────────


def test_create_deadline(client: TestClient) -> None:
    payload = {
        "title": "Test EU AI Act Deadline",
        "category": "eu_ai_act",
        "due_date": "2026-08-02",
        "regulation_reference": "Art. 6",
    }
    r = client.post(f"{BASE}/deadlines", json=payload, headers=_headers())
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Test EU AI Act Deadline"
    assert body["category"] == "eu_ai_act"
    assert body["due_date"] == "2026-08-02"
    assert body["regulation_reference"] == "Art. 6"
    assert body["tenant_id"] == TENANT_A
    assert "id" in body
    assert "escalation_level" in body
    assert "days_remaining" in body
    assert body["created_at_utc"] is not None


# ── 2. List deadlines ─────────────────────────────────────────────────────────


def test_list_deadlines(client: TestClient) -> None:
    # Create two deadlines
    for title in ["Deadline Alpha", "Deadline Beta"]:
        client.post(
            f"{BASE}/deadlines",
            json={"title": title, "category": "custom", "due_date": "2030-01-01"},
            headers=_headers(),
        )
    r = client.get(f"{BASE}/deadlines", headers=_headers())
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    titles = {d["title"] for d in items}
    assert "Deadline Alpha" in titles
    assert "Deadline Beta" in titles


# ── 3. Get deadline ────────────────────────────────────────────────────────────


def test_get_deadline(client: TestClient) -> None:
    cr = client.post(
        f"{BASE}/deadlines",
        json={"title": "Get Me", "category": "nis2", "due_date": "2025-12-31"},
        headers=_headers(),
    )
    deadline_id = cr.json()["id"]
    r = client.get(f"{BASE}/deadlines/{deadline_id}", headers=_headers())
    assert r.status_code == 200
    assert r.json()["title"] == "Get Me"
    assert r.json()["id"] == deadline_id


# ── 4. Update deadline ─────────────────────────────────────────────────────────


def test_update_deadline(client: TestClient) -> None:
    cr = client.post(
        f"{BASE}/deadlines",
        json={"title": "Original", "category": "iso_27001", "due_date": "2027-06-01"},
        headers=_headers(),
    )
    deadline_id = cr.json()["id"]
    r = client.patch(
        f"{BASE}/deadlines/{deadline_id}",
        json={"title": "Updated Title", "due_date": "2028-01-01"},
        headers=_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Updated Title"
    assert body["due_date"] == "2028-01-01"


# ── 5. Delete deadline ─────────────────────────────────────────────────────────


def test_delete_deadline(client: TestClient) -> None:
    cr = client.post(
        f"{BASE}/deadlines",
        json={"title": "To Delete", "category": "dsgvo", "due_date": "2030-01-01"},
        headers=_headers(),
    )
    deadline_id = cr.json()["id"]
    r = client.delete(f"{BASE}/deadlines/{deadline_id}", headers=_headers())
    assert r.status_code == 204
    # Verify it's gone
    r2 = client.get(f"{BASE}/deadlines/{deadline_id}", headers=_headers())
    assert r2.status_code == 404


# ── 6. Seed DACH defaults ─────────────────────────────────────────────────────


def test_seed_dach_defaults(client: TestClient) -> None:
    tenant = "cal-seed-tenant"
    r = client.post(f"{BASE}/seed-defaults", headers=_headers(tenant))
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 6
    titles = {d["title"] for d in items}
    assert "EU AI Act Full Applicability" in titles
    assert "ISO 27001 Re-Certification" in titles
    assert "ISO 42001 Initial Certification" in titles
    assert "DSGVO Art. 33 72h Notification Requirement" in titles
    assert "GoBD §147 Retention Period End" in titles
    assert "NIS2 National Implementation Deadline" in titles
    categories = {d["category"] for d in items}
    assert categories == {"eu_ai_act", "iso_27001", "iso_42001", "dsgvo", "gobd", "nis2"}


# ── 7. Tenant isolation ───────────────────────────────────────────────────────


def test_deadline_tenant_isolation(client: TestClient) -> None:
    # Tenant A creates a deadline
    cr = client.post(
        f"{BASE}/deadlines",
        json={"title": "A-Only", "category": "kritis", "due_date": "2030-06-15"},
        headers=_headers(TENANT_A),
    )
    deadline_id = cr.json()["id"]
    # Tenant B cannot see it
    r = client.get(f"{BASE}/deadlines/{deadline_id}", headers=_headers(TENANT_B))
    assert r.status_code == 404
    # Tenant B list does not contain it
    r2 = client.get(f"{BASE}/deadlines", headers=_headers(TENANT_B))
    titles = {d["title"] for d in r2.json()}
    assert "A-Only" not in titles


# ── 8. iCal export ─────────────────────────────────────────────────────────────


def test_ical_export(client: TestClient) -> None:
    tenant = "cal-ical-tenant"
    client.post(
        f"{BASE}/deadlines",
        json={
            "title": "iCal Test Event",
            "category": "eu_ai_act",
            "due_date": "2026-08-02",
            "regulation_reference": "Art. 113",
        },
        headers=_headers(tenant),
    )
    r = client.get(f"{BASE}/export/ical", headers=_headers(tenant))
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/calendar; charset=utf-8"
    body = r.text
    assert "BEGIN:VCALENDAR" in body
    assert "END:VCALENDAR" in body
    assert "BEGIN:VEVENT" in body
    assert "SUMMARY:iCal Test Event" in body
    assert "DTSTART;VALUE=DATE:20260802" in body
    assert "PRODID:-//ComplianceHub//Compliance Calendar//EN" in body


# ── 9. Escalation levels ──────────────────────────────────────────────────────


def test_escalation_levels() -> None:
    today = date.today()

    # Overdue
    level, days = _compute_escalation(today - timedelta(days=5))
    assert level == EscalationLevel.OVERDUE
    assert days == -5

    # Critical (7 days)
    level, days = _compute_escalation(today + timedelta(days=5))
    assert level == EscalationLevel.CRITICAL
    assert days == 5

    # Warning (14 days)
    level, days = _compute_escalation(today + timedelta(days=10))
    assert level == EscalationLevel.WARNING
    assert days == 10

    # Info (30 days)
    level, days = _compute_escalation(today + timedelta(days=20))
    assert level == EscalationLevel.INFO
    assert days == 20

    # None (>30 days)
    level, days = _compute_escalation(today + timedelta(days=60))
    assert level == EscalationLevel.NONE
    assert days == 60

    # Edge cases
    level, _ = _compute_escalation(today)
    assert level == EscalationLevel.CRITICAL

    level, _ = _compute_escalation(today + timedelta(days=7))
    assert level == EscalationLevel.CRITICAL

    level, _ = _compute_escalation(today + timedelta(days=14))
    assert level == EscalationLevel.WARNING

    level, _ = _compute_escalation(today + timedelta(days=30))
    assert level == EscalationLevel.INFO
