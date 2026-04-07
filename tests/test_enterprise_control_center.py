from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _headers(tenant: str, role: str = "tenant_admin") -> dict[str, str]:
    return {
        "x-api-key": "test-key",
        "x-tenant-id": tenant,
        "x-opa-user-role": role,
    }


def test_control_center_returns_compact_operational_view() -> None:
    tenant = "control-center-tenant-a"

    # Seed at least one incident and one calendar deadline signal.
    incident_resp = client.post(
        "/api/v1/nis2-incidents",
        json={
            "title": "Control center incident",
            "incident_type": "ransomware",
            "severity": "high",
            "summary": "Incident for control center aggregation.",
            "affected_systems": ["erp-1"],
            "kritis_relevant": True,
            "personal_data_affected": False,
        },
        headers=_headers(tenant),
    )
    assert incident_resp.status_code == 201

    deadline_resp = client.post(
        "/api/v1/compliance-calendar/deadlines",
        json={
            "title": "Kurzfristige Frist",
            "category": "nis2",
            "due_date": "2026-04-10",
        },
        headers=_headers(tenant),
    )
    assert deadline_resp.status_code == 201

    resp = client.get(
        "/api/internal/enterprise/control-center?include_markdown=true",
        headers=_headers(tenant),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == tenant
    assert body["summary_counts"]["total_open"] >= 1
    assert isinstance(body["top_urgent_items"], list)
    assert isinstance(body["grouped_sections"], list)
    assert "markdown_de" in body
    sections = {g["section"] for g in body["grouped_sections"]}
    assert "incidents_reporting" in sections
    assert "regulatory_deadlines" in sections
