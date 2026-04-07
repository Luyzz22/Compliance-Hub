from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers(tenant: str) -> dict[str, str]:
    return {
        "x-api-key": "test-key",
        "x-tenant-id": tenant,
        "x-opa-user-role": "tenant_admin",
    }


_HEADERS_A = _headers("nis2-tenant-a")
_HEADERS_B = _headers("nis2-tenant-b")


def _create_payload(**overrides: object) -> dict:
    base: dict = {
        "title": "Ransomware attack on ERP system",
        "incident_type": "ransomware",
        "severity": "high",
        "summary": "Critical ransomware detected on production ERP.",
        "affected_systems": ["erp-prod-01", "erp-prod-02"],
        "kritis_relevant": True,
        "personal_data_affected": True,
        "estimated_impact": "Operational disruption of ERP for ~4 hours.",
    }
    base.update(overrides)
    return base


def test_create_nis2_incident() -> None:
    resp = client.post("/api/v1/nis2-incidents", json=_create_payload(), headers=_HEADERS_A)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Ransomware attack on ERP system"
    assert data["incident_type"] == "ransomware"
    assert data["severity"] == "high"
    assert data["workflow_status"] == "detected"
    assert data["tenant_id"] == "nis2-tenant-a"
    assert data["kritis_relevant"] is True
    assert data["personal_data_affected"] is True
    assert data["affected_systems"] == ["erp-prod-01", "erp-prod-02"]
    assert data["detected_at"] is not None
    assert data["bsi_notification_deadline"] is not None
    assert data["bsi_report_deadline"] is not None
    assert data["contained_at"] is None
    assert data["closed_at"] is None


def test_list_nis2_incidents() -> None:
    # Create two incidents
    client.post(
        "/api/v1/nis2-incidents",
        json=_create_payload(title="Incident list 1"),
        headers=_HEADERS_A,
    )
    client.post(
        "/api/v1/nis2-incidents",
        json=_create_payload(title="Incident list 2"),
        headers=_HEADERS_A,
    )
    resp = client.get("/api/v1/nis2-incidents", headers=_HEADERS_A)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    titles = {d["title"] for d in data}
    assert "Incident list 1" in titles
    assert "Incident list 2" in titles


def test_get_nis2_incident() -> None:
    create_resp = client.post(
        "/api/v1/nis2-incidents",
        json=_create_payload(title="Get by ID test"),
        headers=_HEADERS_A,
    )
    inc_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/nis2-incidents/{inc_id}", headers=_HEADERS_A)
    assert resp.status_code == 200
    assert resp.json()["id"] == inc_id
    assert resp.json()["title"] == "Get by ID test"


def test_get_nis2_incident_not_found() -> None:
    resp = client.get("/api/v1/nis2-incidents/nonexistent-id", headers=_HEADERS_A)
    assert resp.status_code == 404


def test_nis2_incident_workflow_transition() -> None:
    create_resp = client.post(
        "/api/v1/nis2-incidents",
        json=_create_payload(title="Full workflow"),
        headers=_HEADERS_A,
    )
    assert create_resp.status_code == 201
    inc_id = create_resp.json()["id"]
    assert create_resp.json()["workflow_status"] == "detected"

    transitions = [
        ("contained", "contained_at"),
        ("eradicated", "eradicated_at"),
        ("recovered", "recovered_at"),
        ("closed", "closed_at"),
    ]
    for target, ts_field in transitions:
        resp = client.post(
            f"/api/v1/nis2-incidents/{inc_id}/transition",
            json={"target_status": target},
            headers=_HEADERS_A,
        )
        assert resp.status_code == 200, f"Transition to {target} failed: {resp.text}"
        data = resp.json()
        assert data["workflow_status"] == target
        assert data[ts_field] is not None


def test_nis2_incident_invalid_transition() -> None:
    create_resp = client.post(
        "/api/v1/nis2-incidents",
        json=_create_payload(title="Invalid transition test"),
        headers=_HEADERS_A,
    )
    inc_id = create_resp.json()["id"]

    # DETECTED -> RECOVERED is not allowed (must go through CONTAINED first)
    resp = client.post(
        f"/api/v1/nis2-incidents/{inc_id}/transition",
        json={"target_status": "recovered"},
        headers=_HEADERS_A,
    )
    assert resp.status_code == 422


def test_nis2_incident_tenant_isolation() -> None:
    # Create incident for tenant A
    create_resp = client.post(
        "/api/v1/nis2-incidents",
        json=_create_payload(title="Tenant A only"),
        headers=_HEADERS_A,
    )
    inc_id = create_resp.json()["id"]

    # Tenant B cannot see tenant A's incident
    resp = client.get(f"/api/v1/nis2-incidents/{inc_id}", headers=_HEADERS_B)
    assert resp.status_code == 404

    # Tenant B list should not contain tenant A's incident
    resp = client.get("/api/v1/nis2-incidents", headers=_HEADERS_B)
    assert resp.status_code == 200
    ids = {d["id"] for d in resp.json()}
    assert inc_id not in ids


def test_nis2_incident_bsi_deadlines() -> None:
    before = datetime.now(UTC)
    create_resp = client.post(
        "/api/v1/nis2-incidents",
        json=_create_payload(title="BSI deadline test"),
        headers=_HEADERS_A,
    )
    after = datetime.now(UTC)
    data = create_resp.json()

    detected = datetime.fromisoformat(data["detected_at"])
    notif = datetime.fromisoformat(data["bsi_notification_deadline"])
    report = datetime.fromisoformat(data["bsi_report_deadline"])

    # Notification deadline is ~24 hours after detection
    notif_delta = notif - detected
    assert timedelta(hours=23, minutes=59) <= notif_delta <= timedelta(hours=24, minutes=1)

    # Report deadline is ~72 hours after detection
    report_delta = report - detected
    assert timedelta(hours=71, minutes=59) <= report_delta <= timedelta(hours=72, minutes=1)

    # Detected time should be between before and after (with small tolerance)
    detected_utc = detected.replace(tzinfo=UTC)
    assert (before - timedelta(seconds=2)) <= detected_utc <= (after + timedelta(seconds=2))


def test_nis2_final_report_deadline_from_detection() -> None:
    resp = client.post(
        "/api/v1/nis2-incidents",
        json=_create_payload(title="Final report"),
        headers=_HEADERS_A,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["final_report_deadline"] is not None
    detected = datetime.fromisoformat(data["detected_at"])
    report = datetime.fromisoformat(data["bsi_report_deadline"])
    final = datetime.fromisoformat(data["final_report_deadline"])
    assert final - report == timedelta(days=30)
    assert timedelta(hours=71, minutes=59) <= report - detected <= timedelta(hours=72, minutes=1)


def test_nis2_deadline_override_requires_permission() -> None:
    create_resp = client.post(
        "/api/v1/nis2-incidents",
        json=_create_payload(title="Override RBAC"),
        headers=_HEADERS_A,
    )
    inc_id = create_resp.json()["id"]
    low = {
        "x-api-key": "test-key",
        "x-tenant-id": "nis2-tenant-a",
        "x-opa-user-role": "contributor",
    }
    r = client.patch(
        f"/api/v1/nis2-incidents/{inc_id}/deadlines",
        json={
            "bsi_notification_deadline": "2030-01-01T12:00:00+00:00",
            "reason": "documented override for test suite minimum length",
        },
        headers=low,
    )
    assert r.status_code == 403


def test_nis2_deadline_override_and_audit() -> None:
    from app.db import SessionLocal
    from app.repositories.audit_logs import AuditLogRepository

    create_resp = client.post(
        "/api/v1/nis2-incidents",
        json=_create_payload(title="Override ok"),
        headers=_HEADERS_A,
    )
    inc_id = create_resp.json()["id"]
    new_notif = "2031-06-15T08:00:00+00:00"
    r = client.patch(
        f"/api/v1/nis2-incidents/{inc_id}/deadlines",
        json={
            "bsi_notification_deadline": new_notif,
            "reason": "court-approved timeline adjustment for integration testing here",
        },
        headers=_HEADERS_A,
    )
    assert r.status_code == 200
    assert r.json()["bsi_notification_deadline"] is not None

    with SessionLocal() as session:
        arepo = AuditLogRepository(session)
        entries = arepo.list_for_tenant("nis2-tenant-a", limit=50)
        actions = {e.action for e in entries}
        assert "nis2.incident.deadlines.override" in actions
