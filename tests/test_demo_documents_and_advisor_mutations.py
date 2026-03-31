"""Demo read-only: Dokument-Intake und Berater-Snapshot-Report (ohne Tenant-Auth-Pfad)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import DocumentType, EInvoiceFormat
from app.repositories.advisor_tenants import AdvisorTenantRepository
from app.repositories.tenant_registry import TenantRegistryRepository

client = TestClient(app)

ADV = "advisor-demo-ro@example.com"


def _advisor_headers() -> dict[str, str]:
    return {"x-api-key": "board-kpi-key", "x-advisor-id": ADV}


@pytest.fixture
def advisor_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ADVISOR_IDS", ADV)


def test_documents_intake_blocked_for_demo_tenant() -> None:
    tid = f"doc-demo-{uuid.uuid4().hex[:10]}"
    s = SessionLocal()
    try:
        TenantRegistryRepository(s).create(
            tenant_id=tid,
            display_name="Doc Demo",
            industry="IT",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=True,
            demo_playground=False,
        )
    finally:
        s.close()

    r = client.post(
        "/api/v1/documents/intake",
        json={
            "tenant_id": tid,
            "document_id": "d1",
            "document_type": DocumentType.invoice.value,
            "supplier_name": "ACME",
            "supplier_country": "DE",
            "e_invoice_format": EInvoiceFormat.unknown.value,
        },
    )
    assert r.status_code == 403
    d = r.json()["detail"]
    if isinstance(d, dict):
        assert d.get("code") == "demo_tenant_readonly"
    else:
        assert "read-only" in str(d).lower()


def test_advisor_governance_snapshot_report_blocked_for_demo_client(
    advisor_allowlist: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_CLIENT_SNAPSHOT", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_ADVISOR_WORKSPACE", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")

    tid = f"adv-demo-ro-{uuid.uuid4().hex[:8]}"
    s = SessionLocal()
    try:
        TenantRegistryRepository(s).create(
            tenant_id=tid,
            display_name="Client Demo",
            industry="IT",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=True,
            demo_playground=False,
        )
        AdvisorTenantRepository(s).upsert_link(
            advisor_id=ADV,
            tenant_id=tid,
            tenant_display_name="Client Demo",
            industry="IT",
            country="DE",
        )
    finally:
        s.close()

    r = client.post(
        f"/api/v1/advisors/{ADV}/tenants/{tid}/governance-snapshot-report",
        headers=_advisor_headers(),
    )
    assert r.status_code == 403
    d = r.json()["detail"]
    if isinstance(d, dict):
        assert d.get("code") == "demo_tenant_readonly"
