from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, select

from app.ai_impact_assessment_models import AIImpactAssessmentUpsert
from app.db import SessionLocal
from app.db_migrations.migrations import m20260503_ai_impact_assessments as migration
from app.main import app
from app.models_db import AIImpactAssessmentTable, AISystemTable, AuditLogTable
from app.repositories.audit import AuditEventTable


def _headers(tenant_id: str, role: str = "compliance_officer") -> dict[str, str]:
    return {
        "x-api-key": "test-api-key",
        "x-tenant-id": tenant_id,
        "x-opa-user-role": role,
    }


def _create_system(client: TestClient, tenant_id: str, system_id: str) -> None:
    response = client.post(
        "/api/v1/ai-systems",
        headers=_headers(tenant_id, "tenant_admin"),
        json={
            "id": system_id,
            "name": f"Impact Assessment System {system_id}",
            "description": "DPIA and FRIA integration test",
            "business_unit": "Digital Operations",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
        },
    )
    assert response.status_code == 200, response.text


def _sections(status: str = "reviewed") -> list[dict[str, str | None]]:
    keys = [
        "processing_description_and_purpose",
        "necessity_and_proportionality",
        "deployment_period_and_frequency",
        "affected_persons_and_groups",
        "rights_and_freedoms_risks",
        "safeguards_security_and_mitigations",
        "human_oversight_and_governance",
        "incident_complaint_and_redress",
    ]
    return [
        {
            "section_key": key,
            "status": status,
            "summary": f"Controlled assessment summary for {key}.",
            "evidence_reference": f"evidence://impact-assessment/{key}/v1",
            "rationale": "Reviewed against the approved deployment scope.",
        }
        for key in keys
    ]


def _assessment_payload(expected_version: int = 0) -> dict[str, object]:
    return {
        "expected_version": expected_version,
        "dpia_scope": "required",
        "fria_scope": "required",
        "deployer_context": "public_service_provider",
        "scope_rationale": "High-risk deployment with personal-data processing.",
        "lifecycle_status": "approved",
        "residual_risk": "low",
        "assessment_owner": "Privacy Impact Control",
        "independent_reviewer": "Independent Data Protection Review",
        "dpo_involved": True,
        "stakeholder_views_status": "obtained",
        "prior_consultation_status": "not_required",
        "prior_consultation_reference": None,
        "reviewed_at_utc": "2026-08-01T10:00:00+00:00",
        "approved_at_utc": "2026-08-02T10:00:00+00:00",
        "review_due_at_utc": "2026-11-01T10:00:00+00:00",
        "sections": _sections(),
    }


def test_model_enforces_evidence_scope_and_four_eyes() -> None:
    body = _assessment_payload()
    sections = body["sections"]
    assert isinstance(sections, list)
    sections[0]["evidence_reference"] = None
    with pytest.raises(ValidationError, match="evidence_reference"):
        AIImpactAssessmentUpsert.model_validate(body)

    body = _assessment_payload()
    body["assessment_owner"] = body["independent_reviewer"]
    with pytest.raises(ValidationError, match="four-eyes"):
        AIImpactAssessmentUpsert.model_validate(body)

    body = _assessment_payload()
    body["fria_scope"] = "not_required"
    body["scope_rationale"] = None
    with pytest.raises(ValidationError, match="scope_rationale"):
        AIImpactAssessmentUpsert.model_validate(body)


def test_model_blocks_unreviewed_approval_and_open_high_risk_consultation() -> None:
    body = _assessment_payload()
    sections = body["sections"]
    assert isinstance(sections, list)
    sections[2]["status"] = "evidenced"
    with pytest.raises(ValidationError, match="every section reviewed"):
        AIImpactAssessmentUpsert.model_validate(body)

    body = _assessment_payload()
    body["residual_risk"] = "high"
    body["prior_consultation_status"] = "submitted"
    body["prior_consultation_reference"] = "authority-case://dpia/2026-17"
    with pytest.raises(ValidationError, match="prior consultation is closed"):
        AIImpactAssessmentUpsert.model_validate(body)


def test_model_requires_timezone_and_dpo_involvement_for_approved_dpia() -> None:
    body = _assessment_payload()
    body["reviewed_at_utc"] = "2026-08-01T10:00:00"
    with pytest.raises(ValidationError, match="UTC offset"):
        AIImpactAssessmentUpsert.model_validate(body)

    body = _assessment_payload()
    body["dpo_involved"] = False
    with pytest.raises(ValidationError, match="DPO involvement"):
        AIImpactAssessmentUpsert.model_validate(body)


def test_portfolio_defaults_upsert_and_minimized_audit() -> None:
    tenant_id = f"impact-{uuid4().hex[:10]}"
    system_id = f"impact-system-{uuid4().hex[:10]}"
    with TestClient(app) as client:
        _create_system(client, tenant_id, system_id)

        initial = client.get(
            "/api/v1/impact-assessments",
            headers=_headers(tenant_id, "auditor"),
        )
        assert initial.status_code == 200, initial.text
        row = next(item for item in initial.json()["systems"] if item["ai_system_id"] == system_id)
        assert row["posture"] == "scope_incomplete"
        assert row["assessment"]["version"] == 0
        assert len(row["assessment"]["sections"]) == 8
        assert initial.json()["summary"]["scope_open_count"] >= 1

        saved = client.put(
            f"/api/v1/ai-systems/{system_id}/impact-assessment",
            headers=_headers(tenant_id),
            json=_assessment_payload(),
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["version"] == 1
        assert saved.json()["lifecycle_status"] == "approved"

        portfolio = client.get(
            "/api/v1/impact-assessments",
            headers=_headers(tenant_id, "board_member"),
        )
        assert portfolio.status_code == 200, portfolio.text
        saved_row = next(
            item for item in portfolio.json()["systems"] if item["ai_system_id"] == system_id
        )
        assert saved_row["readiness_score_pct"] == 100
        assert saved_row["reviewed_sections"] == 8
        assert saved_row["posture"] == "approved"

    with SessionLocal() as session:
        log = session.scalar(
            select(AuditLogTable)
            .where(
                AuditLogTable.tenant_id == tenant_id,
                AuditLogTable.action == "update_ai_impact_assessment",
            )
            .order_by(AuditLogTable.id.desc())
        )
        assert log is not None
        assert log.entry_hash
        assert "evidence://impact-assessment" not in (log.after or "")
        assert "Independent Data Protection Review" not in (log.after or "")
        assert '"evidence_attached": true' in (log.after or "")


def test_stale_update_is_rejected_without_overwrite() -> None:
    tenant_id = f"impact-version-{uuid4().hex[:8]}"
    system_id = f"impact-version-system-{uuid4().hex[:8]}"
    with TestClient(app) as client:
        _create_system(client, tenant_id, system_id)
        first = client.put(
            f"/api/v1/ai-systems/{system_id}/impact-assessment",
            headers=_headers(tenant_id),
            json=_assessment_payload(),
        )
        assert first.status_code == 200

        stale = client.put(
            f"/api/v1/ai-systems/{system_id}/impact-assessment",
            headers=_headers(tenant_id),
            json=_assessment_payload(expected_version=0),
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "impact_assessment_version_conflict"

        current = client.get(
            f"/api/v1/ai-systems/{system_id}/impact-assessment",
            headers=_headers(tenant_id, "auditor"),
        )
        assert current.status_code == 200
        assert current.json()["version"] == 1


def test_assessment_and_audit_records_share_one_commit_boundary() -> None:
    tenant_id = f"impact-atomic-{uuid4().hex[:8]}"
    system_id = f"impact-atomic-system-{uuid4().hex[:8]}"
    with TestClient(app, raise_server_exceptions=False) as client:
        _create_system(client, tenant_id, system_id)
        with patch(
            "app.ai_impact_assessment_routes.AuditLogRepository.record_event",
            side_effect=RuntimeError("forced hash-audit failure"),
        ):
            response = client.put(
                f"/api/v1/ai-systems/{system_id}/impact-assessment",
                headers=_headers(tenant_id),
                json=_assessment_payload(),
            )
        assert response.status_code == 500

    with SessionLocal() as session:
        assessment = session.scalar(
            select(AIImpactAssessmentTable).where(
                AIImpactAssessmentTable.tenant_id == tenant_id,
                AIImpactAssessmentTable.ai_system_id == system_id,
            )
        )
        normalized_event = session.scalar(
            select(AuditEventTable).where(
                AuditEventTable.tenant_id == tenant_id,
                AuditEventTable.entity_type == "ai_impact_assessment",
                AuditEventTable.entity_id == system_id,
            )
        )
        assert assessment is None
        assert normalized_event is None


def test_tenant_isolation_and_least_privilege_are_enforced() -> None:
    tenant_a = f"impact-a-{uuid4().hex[:8]}"
    tenant_b = f"impact-b-{uuid4().hex[:8]}"
    system_id = f"impact-isolation-{uuid4().hex[:8]}"
    with TestClient(app) as client:
        _create_system(client, tenant_a, system_id)
        saved = client.put(
            f"/api/v1/ai-systems/{system_id}/impact-assessment",
            headers=_headers(tenant_a),
            json=_assessment_payload(),
        )
        assert saved.status_code == 200

        cross_tenant = client.get(
            f"/api/v1/ai-systems/{system_id}/impact-assessment",
            headers=_headers(tenant_b, "auditor"),
        )
        assert cross_tenant.status_code == 404
        tenant_b_portfolio = client.get(
            "/api/v1/impact-assessments",
            headers=_headers(tenant_b, "auditor"),
        )
        assert tenant_b_portfolio.status_code == 200
        assert tenant_b_portfolio.json()["systems"] == []

        viewer_read = client.get(
            "/api/v1/impact-assessments",
            headers=_headers(tenant_a, "viewer"),
        )
        assert viewer_read.status_code == 403
        editor_write = client.put(
            f"/api/v1/ai-systems/{system_id}/impact-assessment",
            headers=_headers(tenant_a, "editor"),
            json=_assessment_payload(expected_version=1),
        )
        assert editor_write.status_code == 403


def test_impact_assessment_migration_is_normalized_and_idempotent() -> None:
    migration_engine = create_engine("sqlite+pysqlite:///:memory:")
    AISystemTable.__table__.create(migration_engine)

    assert migration.apply(migration_engine) is True
    assert migration.apply(migration_engine) is False
    table_names = set(inspect(migration_engine).get_table_names())
    assert "ai_impact_assessments" in table_names
    assert "ai_impact_assessment_sections" in table_names

    indexes = {
        index["name"] for index in inspect(migration_engine).get_indexes("ai_impact_assessments")
    }
    assert "ix_ai_impact_assessments_tenant_review_due" in indexes
    assert "ix_ai_impact_assessments_tenant_lifecycle" in indexes


def test_high_risk_consultation_can_be_approved_when_closed_and_evidenced() -> None:
    body = _assessment_payload()
    body["residual_risk"] = "high"
    body["prior_consultation_status"] = "closed"
    body["prior_consultation_reference"] = "authority-case://dpia/2026-17"
    model = AIImpactAssessmentUpsert.model_validate(body)
    assert model.prior_consultation_status.value == "closed"
    assert model.reviewed_at_utc == datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
