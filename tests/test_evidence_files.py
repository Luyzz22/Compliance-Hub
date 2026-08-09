"""Tests für Evidence-Upload (Storage + DB), Listing, Download, Delete, Tenant-Isolation."""

from __future__ import annotations

import hashlib
import io

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.board_report_audit_records import _records
from tests.conftest import _headers

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@pytest.fixture
def evidence_storage_tmp(tmp_path, monkeypatch: pytest.MonkeyPatch):
    d = tmp_path / "evidence_store"
    monkeypatch.setenv("EVIDENCE_STORAGE_PATH", str(d))
    return d


def _tenant_headers(tenant_id: str) -> dict[str, str]:
    return {**_headers(), "x-tenant-id": tenant_id, "x-opa-user-role": "compliance_officer"}


def _create_ai_system(client: TestClient, tenant_id: str, system_id: str) -> None:
    r = client.post(
        "/api/v1/ai-systems",
        json={
            "id": system_id,
            "name": "Evidence Test System",
            "description": "d",
            "business_unit": "IT",
            "risk_level": "low",
            "ai_act_category": "minimal_risk",
            "gdpr_dpia_required": False,
        },
        headers=_tenant_headers(tenant_id),
    )
    assert r.status_code == 200, r.text


def _create_action(client: TestClient, tenant_id: str) -> str:
    body = {
        "related_ai_system_id": None,
        "related_requirement": "EU_AI_ACT_9",
        "title": "Maßnahme Evidence",
        "status": "open",
    }
    r = client.post(
        "/api/v1/ai-governance/actions",
        json=body,
        headers=_tenant_headers(tenant_id),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _create_audit_record(client: TestClient, tenant_id: str) -> str:
    _records.clear()
    _create_ai_system(client, tenant_id, "ev-audit-sys")
    r = client.post(
        "/api/v1/ai-governance/report/board/audit-records",
        json={"purpose": "Evidence audit", "status": "draft"},
        headers=_tenant_headers(tenant_id),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_evidence_upload_list_download_delete_ai_system(evidence_storage_tmp) -> None:
    tenant = "evidence-tenant-a"
    with TestClient(app) as client:
        _create_ai_system(client, tenant, "ev-sys-1")
        up = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant) | {"x-uploaded-by": "auditor@firma.de"},
            files={"file": ("report.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            data={
                "ai_system_id": "ev-sys-1",
                "norm_framework": "EUAIACT",
                "norm_reference": "Art. 9",
            },
        )
    assert up.status_code == 201, up.text
    ev = up.json()
    assert ev["ai_system_id"] == "ev-sys-1"
    assert ev["filename_original"] == "report.pdf"
    assert ev["content_type"] == "application/pdf"
    assert ev["norm_framework"] == "EUAIACT"
    eid = ev["id"]

    with TestClient(app) as client:
        lst = client.get(
            "/api/v1/evidence",
            params={"ai_system_id": "ev-sys-1"},
            headers=_tenant_headers(tenant),
        )
        assert lst.status_code == 200
        assert len(lst.json()["items"]) == 1

        dl = client.get(
            f"/api/v1/evidence/{eid}/download",
            headers=_tenant_headers(tenant),
        )
        assert dl.status_code == 200
        assert dl.content.startswith(b"%PDF")
        assert "attachment" in dl.headers.get("content-disposition", "")

        de = client.delete(
            f"/api/v1/evidence/{eid}",
            headers=_tenant_headers(tenant),
        )
        assert de.status_code == 204

        dl2 = client.get(
            f"/api/v1/evidence/{eid}/download",
            headers=_tenant_headers(tenant),
        )
        assert dl2.status_code == 404


def test_evidence_tenant_isolation(evidence_storage_tmp) -> None:
    tenant_a = "evidence-tenant-b"
    tenant_c = "evidence-tenant-c"
    with TestClient(app) as client:
        _create_ai_system(client, tenant_a, "ev-sys-a")
        _create_ai_system(client, tenant_c, "ev-sys-c")
        ra = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant_a),
            files={"file": ("a.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            data={"ai_system_id": "ev-sys-a"},
        )
        assert ra.status_code == 201
        eid_a = ra.json()["id"]

        dl_cross = client.get(
            f"/api/v1/evidence/{eid_a}/download",
            headers=_tenant_headers(tenant_c),
        )
        assert dl_cross.status_code == 404

        lst_cross = client.get(
            "/api/v1/evidence",
            params={"ai_system_id": "ev-sys-a"},
            headers=_tenant_headers(tenant_c),
        )
        assert lst_cross.status_code == 200
        assert lst_cross.json()["items"] == []


def test_evidence_invalid_ai_system_wrong_tenant(evidence_storage_tmp) -> None:
    tenant_a = "evidence-tenant-d"
    tenant_b = "evidence-tenant-e"
    with TestClient(app) as client:
        _create_ai_system(client, tenant_a, "only-a")
        r = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant_b),
            files={"file": ("x.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            data={"ai_system_id": "only-a"},
        )
    assert r.status_code == 400
    assert "not found" in r.json()["detail"].lower()


def test_evidence_list_requires_single_filter(evidence_storage_tmp) -> None:
    with TestClient(app) as client:
        r = client.get("/api/v1/evidence", headers=_headers())
        assert r.status_code == 400

        r2 = client.get(
            "/api/v1/evidence",
            params={"ai_system_id": "x", "action_id": "y"},
            headers=_headers(),
        )
        assert r2.status_code == 400


def test_evidence_delete_forbidden_without_key(evidence_storage_tmp, monkeypatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_EVIDENCE_DELETE_API_KEYS", "other-key-not-used")
    tenant = "evidence-tenant-f"
    with TestClient(app) as client:
        _create_ai_system(client, tenant, "ev-sys-f")
        up = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant),
            files={"file": ("f.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            data={"ai_system_id": "ev-sys-f"},
        )
        eid = up.json()["id"]
        de = client.delete(
            f"/api/v1/evidence/{eid}",
            headers=_tenant_headers(tenant),
        )
        assert de.status_code == 403


def test_evidence_upload_for_action(evidence_storage_tmp) -> None:
    tenant = "evidence-tenant-g"
    with TestClient(app) as client:
        aid = _create_action(client, tenant)
        docx_ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        up = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant),
            files={"file": ("sop.docx", io.BytesIO(b"PK\x03\x04fake"), docx_ct)},
            data={"action_id": aid},
        )
        assert up.status_code == 201
        lst = client.get(
            "/api/v1/evidence",
            params={"action_id": aid},
            headers=_tenant_headers(tenant),
        )
        assert len(lst.json()["items"]) == 1


def test_evidence_upload_for_audit_record(evidence_storage_tmp) -> None:
    tenant = "evidence-tenant-h"
    with TestClient(app) as client:
        arid = _create_audit_record(client, tenant)
        xlsx_ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        up = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant),
            files={"file": ("board.xlsx", io.BytesIO(b"PK\x03\x04fake"), xlsx_ct)},
            data={"audit_record_id": arid},
        )
        assert up.status_code == 201
        lst = client.get(
            "/api/v1/evidence",
            params={"audit_record_id": arid},
            headers=_tenant_headers(tenant),
        )
        assert len(lst.json()["items"]) == 1


# ---- Evidence integrity (P0-4) ---------------------------------------------


def test_upload_stores_content_hash(evidence_storage_tmp) -> None:
    """Every upload records a SHA-256 so integrity can later be demonstrated."""
    tenant = "evidence-hash-tenant"
    expected = hashlib.sha256(MINIMAL_PDF).hexdigest()
    with TestClient(app) as client:
        _create_ai_system(client, tenant, "ev-hash-sys")
        up = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant) | {"x-uploaded-by": "auditor@firma.de"},
            files={"file": ("report.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            data={"ai_system_id": "ev-hash-sys"},
        )
    assert up.status_code == 201, up.text
    assert up.json()["sha256"] == expected


def test_verify_detects_tampering(evidence_storage_tmp) -> None:
    """Modifying the stored bytes must surface as a mismatch, not pass silently."""
    tenant = "evidence-verify-tenant"
    with TestClient(app) as client:
        _create_ai_system(client, tenant, "ev-verify-sys")
        up = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant) | {"x-uploaded-by": "auditor@firma.de"},
            files={"file": ("report.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            data={"ai_system_id": "ev-verify-sys"},
        )
        eid = up.json()["id"]

        ok = client.get(f"/api/v1/evidence/{eid}/verify", headers=_tenant_headers(tenant))
        assert ok.status_code == 200, ok.text
        assert ok.json()["status"] == "verified"

        # Tamper with the file behind the application's back, as a DBA or a compromised
        # host could.
        stored = [p for p in evidence_storage_tmp.rglob("*") if p.is_file()]
        assert len(stored) == 1
        stored[0].write_bytes(MINIMAL_PDF + b"tampered")

        bad = client.get(f"/api/v1/evidence/{eid}/verify", headers=_tenant_headers(tenant))
        assert bad.status_code == 200, bad.text
        assert bad.json()["status"] == "mismatch"
        assert bad.json()["expected_sha256"] != bad.json()["actual_sha256"]


def test_verify_is_tenant_isolated(evidence_storage_tmp) -> None:
    tenant_a = "evidence-verify-a"
    tenant_b = "evidence-verify-b"
    with TestClient(app) as client:
        _create_ai_system(client, tenant_a, "ev-iso-sys")
        up = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant_a) | {"x-uploaded-by": "auditor@firma.de"},
            files={"file": ("report.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")},
            data={"ai_system_id": "ev-iso-sys"},
        )
        eid = up.json()["id"]
        cross = client.get(f"/api/v1/evidence/{eid}/verify", headers=_tenant_headers(tenant_b))
    assert cross.status_code == 404


def test_upload_rejects_content_type_mismatch(evidence_storage_tmp) -> None:
    """
    A declared content type must match the actual bytes.

    Content-Type header and file extension are both attacker-controlled, so an allowlist
    built only on them accepts an executable renamed to ``report.pdf`` — which the
    platform would then hand to other users of the same tenant.
    """
    tenant = "evidence-magic-tenant"
    disguised = b"MZ\x90\x00\x03\x00\x00\x00executable payload"
    with TestClient(app) as client:
        _create_ai_system(client, tenant, "ev-magic-sys")
        up = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant) | {"x-uploaded-by": "auditor@firma.de"},
            files={"file": ("report.pdf", io.BytesIO(disguised), "application/pdf")},
            data={"ai_system_id": "ev-magic-sys"},
        )
    assert up.status_code == 400
    assert "does not match declared type" in up.text


def test_upload_accepts_genuine_png(evidence_storage_tmp) -> None:
    """The magic-byte check must not reject legitimate content."""
    tenant = "evidence-png-tenant"
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    with TestClient(app) as client:
        _create_ai_system(client, tenant, "ev-png-sys")
        up = client.post(
            "/api/v1/evidence/uploads",
            headers=_tenant_headers(tenant) | {"x-uploaded-by": "auditor@firma.de"},
            files={"file": ("screenshot.png", io.BytesIO(png), "image/png")},
            data={"ai_system_id": "ev-png-sys"},
        )
    assert up.status_code == 201, up.text
    assert up.json()["sha256"] == hashlib.sha256(png).hexdigest()
