from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app, get_audit_log_repository
from app.repositories.audit_logs import AuditLogRepository
from app.security import get_settings

_TENANT = "gobd-test-tenant"
_TENANT_B = "gobd-test-tenant-b"
_API_KEY = "test-key-1"


def _headers(
    tenant_id: str = _TENANT,
) -> dict[str, str]:
    return {"x-api-key": _API_KEY, "x-tenant-id": tenant_id, "x-opa-user-role": "auditor"}


@pytest.fixture(autouse=True)
def _security_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("COMPLIANCEHUB_API_KEYS", _API_KEY)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def audit_repo() -> Iterator[AuditLogRepository]:
    session = SessionLocal()
    repo = AuditLogRepository(session)

    def _override() -> AuditLogRepository:
        return repo

    app.dependency_overrides[get_audit_log_repository] = _override
    yield repo
    app.dependency_overrides.clear()
    session.close()


@pytest.fixture
def client(audit_repo: AuditLogRepository) -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def test_audit_log_hash_chain_integrity(
    audit_repo: AuditLogRepository,
) -> None:
    """Create several entries and ensure the hash chain links correctly."""
    e1 = audit_repo.record_event(
        tenant_id=_TENANT,
        actor="user-1",
        action="create",
        entity_type="policy",
        entity_id="pol-1",
        before=None,
        after='{"status":"draft"}',
    )
    assert e1.entry_hash is not None
    assert e1.previous_hash is None

    e2 = audit_repo.record_event(
        tenant_id=_TENANT,
        actor="user-1",
        action="update",
        entity_type="policy",
        entity_id="pol-1",
        before='{"status":"draft"}',
        after='{"status":"active"}',
    )
    assert e2.previous_hash == e1.entry_hash
    assert e2.entry_hash is not None
    assert e2.entry_hash != e1.entry_hash

    e3 = audit_repo.record_event(
        tenant_id=_TENANT,
        actor="user-2",
        action="delete",
        entity_type="policy",
        entity_id="pol-1",
        before='{"status":"active"}',
        after=None,
    )
    assert e3.previous_hash == e2.entry_hash


def test_audit_log_gobd_xml_export(
    client: TestClient,
    audit_repo: AuditLogRepository,
) -> None:
    """The GoBD XML endpoint returns well-formed XML with entries."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="xml-actor",
        action="create",
        entity_type="control",
        entity_id="ctrl-1",
        before=None,
        after='{"name":"ctrl"}',
    )

    resp = client.get(
        "/api/v1/audit-logs/export/gobd-xml",
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]

    root = ET.fromstring(resp.text)
    ns = "urn:compliancehub:gobd:audit:v1"
    assert root.tag == f"{{{ns}}}AuditTrail"
    entries = root.findall(f"{{{ns}}}Entry")
    assert len(entries) >= 1

    entry = entries[0]
    assert entry.attrib["action"] == "create"
    assert entry.attrib["entityType"] == "control"
    after_el = entry.find(f"{{{ns}}}After")
    assert after_el is not None
    assert after_el.text is not None


def test_audit_log_hash_chain_verification(
    audit_repo: AuditLogRepository,
) -> None:
    """verify_chain_integrity returns True for a valid chain."""
    tenant = "gobd-chain-verify"
    for i in range(3):
        audit_repo.record_event(
            tenant_id=tenant,
            actor="actor",
            action="update",
            entity_type="doc",
            entity_id=f"doc-{i}",
            before=None,
            after=f'{{"v":{i}}}',
        )
    assert audit_repo.verify_chain_integrity(tenant) is True


def test_audit_log_captures_ip_and_user_agent(
    audit_repo: AuditLogRepository,
) -> None:
    """ip_address and user_agent are stored and returned."""
    entry = audit_repo.record_event(
        tenant_id=_TENANT,
        actor="ua-actor",
        action="login",
        entity_type="session",
        entity_id="sess-1",
        before=None,
        after=None,
        ip_address="192.168.1.42",
        user_agent="Mozilla/5.0 TestAgent",
    )
    assert entry.ip_address == "192.168.1.42"
    assert entry.user_agent == "Mozilla/5.0 TestAgent"


def test_audit_log_gobd_tenant_isolation(
    client: TestClient,
    audit_repo: AuditLogRepository,
) -> None:
    """XML export only returns data for the authenticated tenant."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="actor-a",
        action="create",
        entity_type="risk",
        entity_id="risk-a",
        before=None,
        after="{}",
    )
    audit_repo.record_event(
        tenant_id=_TENANT_B,
        actor="actor-b",
        action="create",
        entity_type="risk",
        entity_id="risk-b",
        before=None,
        after="{}",
    )

    resp = client.get(
        "/api/v1/audit-logs/export/gobd-xml",
        headers=_headers(_TENANT),
    )
    assert resp.status_code == 200
    root = ET.fromstring(resp.text)
    ns = "urn:compliancehub:gobd:audit:v1"
    for entry in root.findall(f"{{{ns}}}Entry"):
        assert entry.attrib["tenantId"] == _TENANT


def test_audit_log_no_update_or_delete_endpoints(
    client: TestClient,
    audit_repo: AuditLogRepository,
) -> None:
    """Audit logs are append-only: PUT, PATCH, DELETE must return 405 Method Not Allowed."""
    audit_repo.record_event(
        tenant_id=_TENANT,
        actor="immutable-actor",
        action="create",
        entity_type="test",
        entity_id="t-1",
        before=None,
        after="{}",
    )
    for method in ("put", "patch", "delete"):
        resp = getattr(client, method)(
            "/api/v1/audit-logs",
            headers=_headers(),
        )
        assert resp.status_code == 405, (
            f"Audit log must be append-only: {method.upper()} should return 405"
        )
