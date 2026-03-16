"""Tests für NormEvidenceLinks (Norm-Nachweise für Board-Report-Audit-Records)."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.board_report_norm_evidence import _links
from tests.conftest import _headers

client = TestClient(app)


def _tenant_headers(tenant_id: str = "board-kpi-tenant") -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-tenant-id": tenant_id}


def _create_audit_record(tenant_id: str = "board-kpi-tenant") -> str:
    """Hilfsfunktion: AI-System + Audit-Record anlegen und ID zurückgeben."""
    resp_sys = client.post(
        "/api/v1/ai-systems",
        json={
            "id": f"ne-sys-{tenant_id}-{uuid4()}",
            "name": "NormEvidence Test System",
            "description": "Test",
            "business_unit": "Ops",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": False,
            "owner_email": "",
            "criticality": "medium",
            "data_sensitivity": "internal",
            "has_incident_runbook": False,
            "has_supplier_risk_register": False,
            "has_backup_runbook": False,
        },
        headers=_tenant_headers(tenant_id),
    )
    assert resp_sys.status_code == 200
    resp = client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={"purpose": "NormEvidence Test", "status": "draft"},
        headers=_tenant_headers(tenant_id),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_and_list_norm_evidence_for_audit_record() -> None:
    """Happy Path: Links anlegen und über GET für Audit-Record abrufen."""
    _links.clear()
    audit_id = _create_audit_record()

    create = client.post(
        f"/api/v1/ai-governance/report/board/audit-records/{audit_id}/norm-evidence",
        json={
            "framework": "EU_AI_ACT",
            "reference": "Art. 9",
            "evidence_type": "board_report",
            "note": "Risikomanagement via Board-Report",
        },
        headers=_headers(),
    )
    assert create.status_code == 201
    links = create.json()
    assert len(links) == 1
    assert links[0]["audit_record_id"] == audit_id
    assert links[0]["framework"] == "EU_AI_ACT"
    assert links[0]["reference"] == "Art. 9"

    get_resp = client.get(
        f"/api/v1/ai-governance/report/board/audit-records/{audit_id}/norm-evidence",
        headers=_headers(),
    )
    assert get_resp.status_code == 200
    got = get_resp.json()
    assert len(got) == 1
    assert got[0]["id"] == links[0]["id"]


def test_norm_evidence_tenant_isolation() -> None:
    """Links von Tenant A sind für Tenant B nicht sichtbar."""
    _links.clear()
    audit_id = _create_audit_record("tenant-ne-a")

    create = client.post(
        f"/api/v1/ai-governance/report/board/audit-records/{audit_id}/norm-evidence",
        json={
            "framework": "NIS2",
            "reference": "Art. 21",
            "evidence_type": "board_report",
        },
        headers=_tenant_headers("tenant-ne-a"),
    )
    assert create.status_code == 201

    resp_b = client.get(
        f"/api/v1/ai-governance/report/board/audit-records/{audit_id}/norm-evidence",
        headers=_tenant_headers("tenant-ne-b"),
    )
    assert resp_b.status_code == 404


def test_query_norm_evidence_by_framework_and_reference() -> None:
    """Query-Endpoint liefert alle Evidenzen für eine Norm-Referenz."""
    _links.clear()
    audit_a = _create_audit_record()
    audit_b = _create_audit_record()

    for audit_id, note in [
        (audit_a, "Art. 9 Evidence A"),
        (audit_b, "Art. 9 Evidence B"),
    ]:
        resp = client.post(
            f"/api/v1/ai-governance/report/board/audit-records/{audit_id}/norm-evidence",
            json={
                "framework": "EU_AI_ACT",
                "reference": "Art. 9",
                "evidence_type": "board_report",
                "note": note,
            },
            headers=_headers(),
        )
        assert resp.status_code == 201

    query_resp = client.get(
        "/api/v1/ai-governance/norm-evidence?framework=EU_AI_ACT&reference=Art. 9",
        headers=_headers(),
    )
    assert query_resp.status_code == 200
    items = query_resp.json()
    assert len(items) >= 2
    audit_ids = {item["audit_record_id"] for item in items}
    assert audit_a in audit_ids and audit_b in audit_ids


def test_norm_evidence_401_no_api_key() -> None:
    """POST ohne API-Key → 401."""
    _links.clear()
    audit_id = _create_audit_record()
    resp = client.post(
        f"/api/v1/ai-governance/report/board/audit-records/{audit_id}/norm-evidence",
        json={
            "framework": "EU_AI_ACT",
            "reference": "Art. 9",
            "evidence_type": "board_report",
        },
        headers={"x-tenant-id": "board-kpi-tenant"},
    )
    assert resp.status_code == 401


def test_norm_evidence_401_invalid_api_key() -> None:
    """GET mit ungültigem API-Key → 401."""
    _links.clear()
    audit_id = _create_audit_record()
    resp = client.get(
        f"/api/v1/ai-governance/report/board/audit-records/{audit_id}/norm-evidence",
        headers={"x-api-key": "invalid", "x-tenant-id": "board-kpi-tenant"},
    )
    assert resp.status_code == 401
