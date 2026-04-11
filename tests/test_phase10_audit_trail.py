"""Phase 10 – Enterprise Audit Trail, NIS2 Alerts, VVT Export tests."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app, get_audit_log_repository
from app.repositories.audit_logs import AuditLogRepository
from app.security import get_settings
from app.services.audit_trail_service import AuditTrailService, NIS2AlertService
from app.services.audit_trail_types import AlertSeverity

_TENANT = "phase10-test-tenant"
_API_KEY = "test-key-1"


def _headers(
    tenant_id: str = _TENANT,
    *,
    opa_role: str = "tenant_admin",
) -> dict[str, str]:
    return {
        "x-api-key": _API_KEY,
        "x-tenant-id": tenant_id,
        "x-opa-user-role": opa_role,
    }


@pytest.fixture(autouse=True)
def _security_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("COMPLIANCEHUB_API_KEYS", _API_KEY)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def session() -> Iterator[Session]:
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture
def audit_repo(session: Session) -> AuditLogRepository:
    repo = AuditLogRepository(session)

    def _override() -> AuditLogRepository:
        return repo

    app.dependency_overrides[get_audit_log_repository] = _override
    return repo


@pytest.fixture
def client(audit_repo: AuditLogRepository) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---- AuditTrailService tests ----


def test_list_filtered_returns_page(session: Session, audit_repo: AuditLogRepository) -> None:
    """Filtered listing returns a properly structured page."""
    for i in range(3):
        audit_repo.record_event(
            tenant_id=_TENANT,
            actor=f"actor-{i}",
            action="create",
            entity_type="policy",
            entity_id=f"pol-{i}",
            before=None,
            after=f'{{"v":{i}}}',
        )
    svc = AuditTrailService(session)
    page = svc.list_filtered(_TENANT, page=1, page_size=2)
    assert page.total == 3
    assert len(page.items) == 2
    assert page.has_next is True
    assert page.page == 1


def test_list_filtered_actor_filter(session: Session, audit_repo: AuditLogRepository) -> None:
    """Filter by actor returns only matching entries."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="alice",
        action="login",
        entity_type="session",
        entity_id="s1",
        before=None,
        after=None,
    )
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="bob",
        action="login",
        entity_type="session",
        entity_id="s2",
        before=None,
        after=None,
    )
    svc = AuditTrailService(session)
    page = svc.list_filtered(_TENANT, actor="alice")
    assert page.total == 1
    assert page.items[0].actor == "alice"


def test_verify_integrity_valid(session: Session, audit_repo: AuditLogRepository) -> None:
    """Chain integrity check returns valid for a clean chain."""
    for i in range(3):
        audit_repo.record_event(
            tenant_id=_TENANT,
            actor="actor",
            action="update",
            entity_type="doc",
            entity_id=f"doc-{i}",
            before=None,
            after=f'{{"v":{i}}}',
        )
    svc = AuditTrailService(session)
    result = svc.verify_integrity(_TENANT)
    assert result.valid is True
    assert result.checked_count >= 3


def test_export_csv_format(session: Session, audit_repo: AuditLogRepository) -> None:
    """CSV export produces valid CSV with header and entries."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="csv-test",
        action="create",
        entity_type="risk",
        entity_id="r1",
        before=None,
        after="{}",
    )
    svc = AuditTrailService(session)
    csv_text = svc.export_csv(_TENANT)
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)
    assert rows[0][0] == "id"
    assert len(rows) >= 2  # header + at least 1 data row


def test_export_json_format(session: Session, audit_repo: AuditLogRepository) -> None:
    """JSON export produces valid JSON array."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="json-test",
        action="update",
        entity_type="control",
        entity_id="c1",
        before=None,
        after="{}",
    )
    svc = AuditTrailService(session)
    json_text = svc.export_json(_TENANT)
    data = json.loads(json_text)
    assert isinstance(data, list)
    assert len(data) >= 1


def test_vvt_export_structure(session: Session, audit_repo: AuditLogRepository) -> None:
    """VVT export generates entries grouped by action."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="vvt-test",
        action="login",
        entity_type="session",
        entity_id="s1",
        before=None,
        after=None,
    )
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="vvt-test",
        action="update",
        entity_type="policy",
        entity_id="p1",
        before=None,
        after="{}",
    )
    svc = AuditTrailService(session)
    vvt = svc.generate_vvt_export(_TENANT)
    assert vvt.tenant_id == _TENANT
    assert vvt.total_processing_activities >= 2
    activities = [e.processing_activity for e in vvt.entries]
    assert "login" in activities
    assert "update" in activities


# ---- NIS2AlertService tests ----


def test_create_and_list_alert(session: Session) -> None:
    """Create an alert and list it."""
    svc = NIS2AlertService(session)
    alert = svc.create_alert(
        tenant_id=_TENANT,
        severity=AlertSeverity.HIGH,
        alert_type="failed_logins",
        title="3x fehlgeschlagene Logins",
        actor="unknown@extern.de",
        ip_address="203.0.113.42",
    )
    assert alert.severity == "HIGH"
    assert alert.resolved is False

    alerts = svc.list_alerts(_TENANT)
    assert len(alerts) >= 1
    assert any(a.id == alert.id for a in alerts)


def test_resolve_alert(session: Session) -> None:
    """Resolve an alert and verify fields update."""
    svc = NIS2AlertService(session)
    alert = svc.create_alert(
        tenant_id=_TENANT,
        severity=AlertSeverity.MEDIUM,
        alert_type="unknown_ip",
        title="Zugriff von unbekannter IP",
    )
    resolved = svc.resolve_alert(_TENANT, alert.id, resolved_by="admin@sbs.de")
    assert resolved is not None
    assert resolved.resolved is True
    assert resolved.resolved_by == "admin@sbs.de"


def test_list_alerts_severity_filter(session: Session) -> None:
    """Listing with severity filter only returns matching alerts."""
    svc = NIS2AlertService(session)
    svc.create_alert(
        tenant_id=_TENANT,
        severity=AlertSeverity.LOW,
        alert_type="info",
        title="Low alert",
    )
    svc.create_alert(
        tenant_id=_TENANT,
        severity=AlertSeverity.CRITICAL,
        alert_type="escalation",
        title="Critical alert",
    )
    critical = svc.list_alerts(_TENANT, severity="CRITICAL")
    assert all(a.severity == "CRITICAL" for a in critical)


# ---- API endpoint tests ----


def test_api_filtered_logs(client: TestClient, audit_repo: AuditLogRepository) -> None:
    """GET /api/v1/audit-logs/filtered returns paginated data."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="api-test",
        action="create",
        entity_type="risk",
        entity_id="r1",
        before=None,
        after="{}",
    )
    resp = client.get(
        "/api/v1/audit-logs/filtered",
        headers=_headers(opa_role="contributor"),
        params={"page": 1, "page_size": 10},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1


def test_api_integrity_check(client: TestClient, audit_repo: AuditLogRepository) -> None:
    """GET /api/v1/audit-logs/integrity returns chain status."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="integrity-test",
        action="create",
        entity_type="x",
        entity_id="y",
        before=None,
        after="{}",
    )
    resp = client.get(
        "/api/v1/audit-logs/integrity",
        headers=_headers(opa_role="auditor"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True


def test_api_csv_export(client: TestClient, audit_repo: AuditLogRepository) -> None:
    """GET /api/v1/audit-logs/export/csv returns CSV."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="csv-api",
        action="create",
        entity_type="x",
        entity_id="y",
        before=None,
        after="{}",
    )
    resp = client.get(
        "/api/v1/audit-logs/export/csv",
        headers=_headers(opa_role="auditor"),
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "id,timestamp" in resp.text


def test_api_json_export(client: TestClient, audit_repo: AuditLogRepository) -> None:
    """GET /api/v1/audit-logs/export/json returns JSON."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="json-api",
        action="create",
        entity_type="x",
        entity_id="y",
        before=None,
        after="{}",
    )
    resp = client.get(
        "/api/v1/audit-logs/export/json",
        headers=_headers(opa_role="auditor"),
    )
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    data = json.loads(resp.text)
    assert isinstance(data, list)


def test_api_vvt_export(client: TestClient, audit_repo: AuditLogRepository) -> None:
    """GET /api/v1/audit-logs/vvt-export returns VVT structure."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="vvt-api",
        action="login",
        entity_type="session",
        entity_id="s1",
        before=None,
        after=None,
    )
    resp = client.get(
        "/api/v1/audit-logs/vvt-export",
        headers=_headers(opa_role="auditor"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == _TENANT
    assert "entries" in body


def test_api_export_forbidden_for_viewer(
    client: TestClient, audit_repo: AuditLogRepository
) -> None:
    """Viewer cannot export audit logs."""
    resp = client.get(
        "/api/v1/audit-logs/export/csv",
        headers=_headers(opa_role="viewer"),
    )
    assert resp.status_code == 403


def test_alert_severity_enum() -> None:
    """AlertSeverity enum has expected values."""
    assert AlertSeverity.LOW == "LOW"
    assert AlertSeverity.MEDIUM == "MEDIUM"
    assert AlertSeverity.HIGH == "HIGH"
    assert AlertSeverity.CRITICAL == "CRITICAL"
