from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.compliance_calendar_models import DeadlineStatus, EscalationLevel
from app.main import app
from app.repositories.compliance_deadlines import _compute_escalation

TENANT_A = "cal-test-tenant-a"
TENANT_B = "cal-test-tenant-b"
API_KEY = "test-key"
BASE = "/api/v1/compliance-calendar"


def _headers(tenant: str = TENANT_A, *, opa_role: str = "tenant_admin") -> dict[str, str]:
    return {
        "x-api-key": API_KEY,
        "x-tenant-id": tenant,
        "x-opa-user-role": opa_role,
    }


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


def test_seed_dach_defaults_idempotent(client: TestClient) -> None:
    tenant = "cal-seed-idempotent"
    r1 = client.post(f"{BASE}/seed-defaults", headers=_headers(tenant))
    r2 = client.post(f"{BASE}/seed-defaults", headers=_headers(tenant))
    assert r1.status_code == 200 and r2.status_code == 200
    lst = client.get(f"{BASE}/deadlines", headers=_headers(tenant, opa_role="viewer"))
    assert lst.status_code == 200
    assert len(lst.json()) == 6


def test_compliance_calendar_mutations_forbidden_for_contributor(client: TestClient) -> None:
    r = client.post(
        f"{BASE}/deadlines",
        json={"title": "X", "category": "custom", "due_date": "2031-01-01"},
        headers=_headers(opa_role="contributor"),
    )
    assert r.status_code == 403


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


# ── 10. System deadlines ──────────────────────────────────────────────────────


def test_seed_system_deadlines(client: TestClient) -> None:
    r = client.post(
        f"{BASE}/seed-system-deadlines",
        headers=_headers("sys-seed-tenant"),
    )
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 8
    for item in items:
        assert item["is_system"] is True
        assert item["tenant_id"] is None
    titles = {d["title"] for d in items}
    assert "EU AI Act – Vollständige Anwendbarkeit" in titles
    assert "EU AI Act – Verbotene Systeme" in titles
    assert "EU AI Act – GPAI-Modelle" in titles
    assert "DSGVO Art. 33 – 72h-Meldefrist" in titles
    assert "GoBD §147 – 10-Jahre-Aufbewahrungsfrist" in titles
    assert "KRITIS / BSI-KritisV – Registrierungsfristen" in titles


def test_seed_system_deadlines_idempotent(client: TestClient) -> None:
    t = "sys-seed-idem"
    r1 = client.post(f"{BASE}/seed-system-deadlines", headers=_headers(t))
    r2 = client.post(f"{BASE}/seed-system-deadlines", headers=_headers(t))
    assert r1.status_code == 200 and r2.status_code == 200
    assert len(r1.json()) == len(r2.json())


def test_system_deadlines_visible_to_all_tenants(
    client: TestClient,
) -> None:
    # Seed system deadlines
    client.post(
        f"{BASE}/seed-system-deadlines",
        headers=_headers("sys-visible-seeder"),
    )
    # Both tenants can see system deadlines in their list
    for tenant in ["sys-vis-a", "sys-vis-b"]:
        r = client.get(f"{BASE}/deadlines", headers=_headers(tenant))
        assert r.status_code == 200
        system_items = [
            d for d in r.json() if d["is_system"] is True
        ]
        assert len(system_items) >= 8


def test_system_deadline_readable_by_id(client: TestClient) -> None:
    client.post(
        f"{BASE}/seed-system-deadlines",
        headers=_headers("sys-read-seeder"),
    )
    r = client.get(
        f"{BASE}/deadlines",
        headers=_headers("sys-read-tenant"),
    )
    system_items = [d for d in r.json() if d["is_system"] is True]
    assert len(system_items) > 0
    sid = system_items[0]["id"]
    r2 = client.get(
        f"{BASE}/deadlines/{sid}",
        headers=_headers("sys-read-tenant"),
    )
    assert r2.status_code == 200
    assert r2.json()["is_system"] is True


# ── 11. is_system guard (update/delete forbidden) ────────────────────────────


def test_update_system_deadline_returns_403(client: TestClient) -> None:
    client.post(
        f"{BASE}/seed-system-deadlines",
        headers=_headers("sys-guard-upd"),
    )
    r = client.get(f"{BASE}/deadlines", headers=_headers("sys-guard-upd"))
    system_items = [d for d in r.json() if d["is_system"] is True]
    sid = system_items[0]["id"]
    r2 = client.patch(
        f"{BASE}/deadlines/{sid}",
        json={"title": "Hacked"},
        headers=_headers("sys-guard-upd"),
    )
    assert r2.status_code == 403
    assert "System deadlines" in r2.json()["detail"]


def test_delete_system_deadline_returns_403(client: TestClient) -> None:
    client.post(
        f"{BASE}/seed-system-deadlines",
        headers=_headers("sys-guard-del"),
    )
    r = client.get(f"{BASE}/deadlines", headers=_headers("sys-guard-del"))
    system_items = [d for d in r.json() if d["is_system"] is True]
    sid = system_items[0]["id"]
    r2 = client.delete(
        f"{BASE}/deadlines/{sid}",
        headers=_headers("sys-guard-del"),
    )
    assert r2.status_code == 403
    assert "System deadlines" in r2.json()["detail"]


# ── 12. Upcoming endpoint ─────────────────────────────────────────────────────


def test_upcoming_deadlines(client: TestClient) -> None:
    tenant = "cal-upcoming-test"
    today = date.today()
    # Create one upcoming and one far-future deadline
    client.post(
        f"{BASE}/deadlines",
        json={
            "title": "Soon",
            "category": "custom",
            "due_date": (today + timedelta(days=10)).isoformat(),
        },
        headers=_headers(tenant),
    )
    client.post(
        f"{BASE}/deadlines",
        json={
            "title": "Far Away",
            "category": "custom",
            "due_date": (today + timedelta(days=365)).isoformat(),
        },
        headers=_headers(tenant),
    )
    r = client.get(
        f"{BASE}/deadlines/upcoming?days=30",
        headers=_headers(tenant),
    )
    assert r.status_code == 200
    titles = {d["title"] for d in r.json()}
    assert "Soon" in titles
    assert "Far Away" not in titles


# ── 13. Status field ──────────────────────────────────────────────────────────


def test_create_deadline_with_status(client: TestClient) -> None:
    r = client.post(
        f"{BASE}/deadlines",
        json={
            "title": "In Progress Deadline",
            "category": "custom",
            "due_date": "2030-01-01",
            "status": "in_progress",
        },
        headers=_headers("cal-status-test"),
    )
    assert r.status_code == 201
    assert r.json()["status"] == "in_progress"


def test_update_deadline_status(client: TestClient) -> None:
    cr = client.post(
        f"{BASE}/deadlines",
        json={
            "title": "Status Update",
            "category": "custom",
            "due_date": "2030-01-01",
        },
        headers=_headers("cal-status-upd"),
    )
    did = cr.json()["id"]
    r = client.patch(
        f"{BASE}/deadlines/{did}",
        json={"status": "completed"},
        headers=_headers("cal-status-upd"),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


def test_overdue_status_auto_set(client: TestClient) -> None:
    r = client.post(
        f"{BASE}/deadlines",
        json={
            "title": "Overdue Auto",
            "category": "custom",
            "due_date": "2020-01-01",
        },
        headers=_headers("cal-overdue-auto"),
    )
    assert r.status_code == 201
    assert r.json()["status"] == "overdue"


# ── 14. iCal export contains no PII ──────────────────────────────────────────


def test_ical_export_no_pii(client: TestClient) -> None:
    tenant = "cal-ical-nopii"
    client.post(
        f"{BASE}/deadlines",
        json={
            "title": "PII Check",
            "category": "dsgvo",
            "due_date": "2027-01-01",
            "owner": "john.doe@example.com",
        },
        headers=_headers(tenant),
    )
    r = client.get(f"{BASE}/export/ical", headers=_headers(tenant))
    assert r.status_code == 200
    body = r.text
    # Owner email must not appear in iCal export
    assert "john.doe@example.com" not in body
    assert "ORGANIZER" not in body


# ── 15. DeadlineStatus enum ──────────────────────────────────────────────────


def test_deadline_status_enum_values() -> None:
    assert DeadlineStatus.OPEN == "open"
    assert DeadlineStatus.IN_PROGRESS == "in_progress"
    assert DeadlineStatus.COMPLETED == "completed"
    assert DeadlineStatus.OVERDUE == "overdue"
