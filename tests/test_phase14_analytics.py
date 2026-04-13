"""Tests for Phase 14 – Compliance Analytics KPI Service & Endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models_db import (
    AuditAlertDB,
    AuditLogTable,
    Base,
    ComplianceControlDB,
    ComplianceFrameworkDB,
    ComplianceRequirementControlLinkDB,
    ComplianceRequirementDB,
    TrustCenterAccessLogDB,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _engine(tmp_path):
    db_path = tmp_path / "analytics_test.db"
    url = f"sqlite+pysqlite:///{db_path}"
    engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def _session(_engine):
    sm = sessionmaker(bind=_engine)
    session = sm()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------


def test_compliance_score_empty(_session) -> None:
    """Score is 0.0 when no controls exist for the tenant."""
    from app.services.analytics_service import get_compliance_score

    result = get_compliance_score(_session, "tenant-empty")
    assert result["score"] == 0.0
    assert result["total_controls"] == 0
    assert result["implemented_controls"] == 0


def test_compliance_score_with_controls(_session) -> None:
    """Score reflects ratio of implemented+verified controls."""
    from app.services.analytics_service import get_compliance_score

    _session.add_all(
        [
            ComplianceControlDB(
                id="c1", tenant_id="t1", name="C1", control_type="technical", status="implemented"
            ),
            ComplianceControlDB(
                id="c2", tenant_id="t1", name="C2", control_type="technical", status="verified"
            ),
            ComplianceControlDB(
                id="c3", tenant_id="t1", name="C3", control_type="organisational", status="planned"
            ),
            ComplianceControlDB(
                id="c4",
                tenant_id="t1",
                name="C4",
                control_type="organisational",
                status="planned",
            ),
        ]
    )
    _session.commit()

    result = get_compliance_score(_session, "t1")
    assert result["total_controls"] == 4
    assert result["implemented_controls"] == 2
    assert result["score"] == 50.0


def test_risk_matrix_empty(_session) -> None:
    """Risk matrix returns zeros when no alerts exist."""
    from app.services.analytics_service import get_risk_matrix

    result = get_risk_matrix(_session, "t-none")
    assert result["critical"] == 0
    assert result["high"] == 0
    assert result["total"] == 0


def test_risk_matrix_with_alerts(_session) -> None:
    """Risk matrix counts unresolved alerts by severity."""
    from app.services.analytics_service import get_risk_matrix

    _session.add_all(
        [
            AuditAlertDB(
                id="a1",
                tenant_id="t2",
                severity="CRITICAL",
                alert_type="test",
                title="Alert 1",
                resolved=False,
            ),
            AuditAlertDB(
                id="a2",
                tenant_id="t2",
                severity="HIGH",
                alert_type="test",
                title="Alert 2",
                resolved=False,
            ),
            AuditAlertDB(
                id="a3",
                tenant_id="t2",
                severity="HIGH",
                alert_type="test",
                title="Alert 3 (resolved)",
                resolved=True,
            ),
        ]
    )
    _session.commit()

    result = get_risk_matrix(_session, "t2")
    assert result["critical"] == 1
    assert result["high"] == 1
    assert result["total"] == 2


def test_activity_feed_empty(_session) -> None:
    """Activity feed returns empty list when no logs exist."""
    from app.services.analytics_service import get_activity_feed

    result = get_activity_feed(_session, "t-none")
    assert result == []


def test_activity_feed_returns_entries(_session) -> None:
    """Activity feed returns the most recent audit log entries."""
    from app.services.analytics_service import get_activity_feed

    _session.add(
        AuditLogTable(
            tenant_id="t3",
            actor="admin@test.de",
            action="create_control",
            entity_type="compliance_control",
            entity_id="ctrl-1",
        )
    )
    _session.commit()

    result = get_activity_feed(_session, "t3", limit=5)
    assert len(result) == 1
    assert result[0]["actor"] == "admin@test.de"
    assert result[0]["action"] == "create_control"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


def test_analytics_kpi_summary_requires_auth() -> None:
    """Analytics KPI summary endpoint requires proper auth."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/analytics/kpi-summary")
    assert resp.status_code in (400, 401, 403, 422)


def test_analytics_compliance_score_requires_auth() -> None:
    """Analytics compliance score requires proper auth."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/v1/analytics/compliance-score")
    assert resp.status_code in (400, 401, 403, 422)


def test_analytics_viewer_denied() -> None:
    """Viewer role cannot access analytics endpoints."""
    from app.main import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get(
        "/api/v1/analytics/compliance-score",
        headers={
            "x-api-key": "test-key",
            "x-tenant-id": "test-tenant",
            "x-opa-user-role": "viewer",
        },
    )
    assert resp.status_code == 403
