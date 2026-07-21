from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, select

from app.ai_transparency_assurance_models import AITransparencyAssessmentUpsert
from app.db import SessionLocal
from app.db_migrations.migrations import m20260502_ai_transparency_assurance as migration
from app.main import app
from app.models_db import AISystemTable, AITransparencyAssessmentTable, AuditLogTable
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
            "name": f"Article 50 System {system_id}",
            "description": "Assurance integration test",
            "business_unit": "Digital Products",
            "risk_level": "high",
            "ai_act_category": "limited_risk",
            "gdpr_dpia_required": True,
        },
    )
    assert response.status_code == 200, response.text


def _control_payloads() -> list[dict[str, str | None]]:
    return [
        {
            "control_key": "ai_interaction_disclosure",
            "status": "verified",
            "evidence_reference": "evidence://notice-release-42",
            "rationale": "Notice shown on first interaction and accessibility tested.",
        },
        {
            "control_key": "synthetic_content_marking",
            "status": "implemented",
            "evidence_reference": "evidence://c2pa-test-17",
            "rationale": "Release implemented; independent verification is scheduled.",
        },
        {
            "control_key": "emotion_biometric_notice",
            "status": "not_applicable",
            "evidence_reference": None,
            "rationale": (
                "System performs neither emotion recognition nor biometric categorisation."
            ),
        },
        {
            "control_key": "deepfake_disclosure",
            "status": "not_applicable",
            "evidence_reference": None,
            "rationale": "System does not generate or manipulate image, audio or video content.",
        },
        {
            "control_key": "public_interest_text_review_or_disclosure",
            "status": "not_applicable",
            "evidence_reference": None,
            "rationale": "No public-interest publication is within the approved use case.",
        },
        {
            "control_key": "gdpr_transparency_notice",
            "status": "not_applicable",
            "evidence_reference": None,
            "rationale": "No personal data processing occurs in the approved deployment scope.",
        },
    ]


def _assessment_payload(expected_version: int = 0) -> dict[str, object]:
    return {
        "expected_version": expected_version,
        "role_scope": "provider",
        "control_owner": "AI Product Control",
        "reviewer": "Data Protection Review",
        "reviewed_at_utc": "2026-07-20T10:00:00+00:00",
        "review_due_at_utc": "2026-10-20T10:00:00+00:00",
        "controls": _control_payloads(),
    }


def test_model_rejects_unsubstantiated_verification_and_na_rationale_gap() -> None:
    body = _assessment_payload()
    controls = body["controls"]
    assert isinstance(controls, list)
    controls[0]["evidence_reference"] = None
    controls[2]["rationale"] = None
    with pytest.raises(ValidationError) as exc_info:
        AITransparencyAssessmentUpsert.model_validate(body)
    assert "evidence_reference" in str(exc_info.value)


def test_model_enforces_four_eyes_and_timezone_aware_review() -> None:
    body = _assessment_payload()
    body["reviewer"] = body["control_owner"]
    with pytest.raises(ValidationError, match="four-eyes"):
        AITransparencyAssessmentUpsert.model_validate(body)

    body = _assessment_payload()
    body["reviewed_at_utc"] = "2026-07-20T10:00:00"
    with pytest.raises(ValidationError, match="UTC offset"):
        AITransparencyAssessmentUpsert.model_validate(body)


def test_assurance_register_defaults_upsert_summary_and_audit_minimization() -> None:
    tenant_id = f"transparency-{uuid4().hex[:10]}"
    system_id = f"article50-{uuid4().hex[:10]}"
    with TestClient(app) as client:
        _create_system(client, tenant_id, system_id)

        initial = client.get(
            "/api/v1/transparency-assurance",
            headers=_headers(tenant_id, "auditor"),
        )
        assert initial.status_code == 200, initial.text
        initial_body = initial.json()
        row = next(item for item in initial_body["systems"] if item["ai_system_id"] == system_id)
        assert row["posture"] == "requires_scope"
        assert row["assessment"]["version"] == 0
        assert len(row["assessment"]["controls"]) == 6
        assert initial_body["summary"]["requires_scope_count"] >= 1

        saved = client.put(
            f"/api/v1/ai-systems/{system_id}/transparency-assurance",
            headers=_headers(tenant_id),
            json=_assessment_payload(),
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["version"] == 1
        assert saved.json()["role_scope"] == "provider"

        summary = client.get(
            "/api/v1/transparency-assurance",
            headers=_headers(tenant_id, "board_member"),
        )
        assert summary.status_code == 200, summary.text
        saved_row = next(
            item for item in summary.json()["systems"] if item["ai_system_id"] == system_id
        )
        assert saved_row["readiness_score_pct"] == 88
        assert saved_row["applicable_controls"] == 2
        assert saved_row["verified_controls"] == 1
        assert saved_row["posture"] == "implementation_pending_verification"

    with SessionLocal() as session:
        log = session.scalar(
            select(AuditLogTable)
            .where(
                AuditLogTable.tenant_id == tenant_id,
                AuditLogTable.action == "update_transparency_assurance",
            )
            .order_by(AuditLogTable.id.desc())
        )
        assert log is not None
        assert log.entry_hash
        assert "evidence://notice-release-42" not in (log.after or "")
        assert "Data Protection Review" not in (log.after or "")
        assert '"evidence_attached": true' in (log.after or "")


def test_stale_update_is_rejected_without_overwrite() -> None:
    tenant_id = f"transparency-version-{uuid4().hex[:8]}"
    system_id = f"article50-version-{uuid4().hex[:8]}"
    with TestClient(app) as client:
        _create_system(client, tenant_id, system_id)
        first = client.put(
            f"/api/v1/ai-systems/{system_id}/transparency-assurance",
            headers=_headers(tenant_id),
            json=_assessment_payload(),
        )
        assert first.status_code == 200

        stale = client.put(
            f"/api/v1/ai-systems/{system_id}/transparency-assurance",
            headers=_headers(tenant_id),
            json=_assessment_payload(expected_version=0),
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "transparency_assessment_version_conflict"

        current = client.get(
            f"/api/v1/ai-systems/{system_id}/transparency-assurance",
            headers=_headers(tenant_id, "auditor"),
        )
        assert current.status_code == 200
        assert current.json()["version"] == 1


def test_assessment_and_both_audit_records_share_one_commit_boundary() -> None:
    tenant_id = f"transparency-atomic-{uuid4().hex[:8]}"
    system_id = f"article50-atomic-{uuid4().hex[:8]}"
    with TestClient(app, raise_server_exceptions=False) as client:
        _create_system(client, tenant_id, system_id)
        with patch(
            "app.ai_transparency_assurance_routes.AuditLogRepository.record_event",
            side_effect=RuntimeError("forced hash-audit failure"),
        ):
            response = client.put(
                f"/api/v1/ai-systems/{system_id}/transparency-assurance",
                headers=_headers(tenant_id),
                json=_assessment_payload(),
            )
        assert response.status_code == 500

    with SessionLocal() as session:
        assessment = session.scalar(
            select(AITransparencyAssessmentTable).where(
                AITransparencyAssessmentTable.tenant_id == tenant_id,
                AITransparencyAssessmentTable.ai_system_id == system_id,
            )
        )
        normalized_event = session.scalar(
            select(AuditEventTable).where(
                AuditEventTable.tenant_id == tenant_id,
                AuditEventTable.entity_type == "ai_transparency_assessment",
                AuditEventTable.entity_id == system_id,
            )
        )
        assert assessment is None
        assert normalized_event is None


def test_tenant_isolation_and_least_privilege_are_enforced() -> None:
    tenant_a = f"transparency-a-{uuid4().hex[:8]}"
    tenant_b = f"transparency-b-{uuid4().hex[:8]}"
    system_id = f"article50-isolation-{uuid4().hex[:8]}"
    with TestClient(app) as client:
        _create_system(client, tenant_a, system_id)
        saved = client.put(
            f"/api/v1/ai-systems/{system_id}/transparency-assurance",
            headers=_headers(tenant_a),
            json=_assessment_payload(),
        )
        assert saved.status_code == 200

        cross_tenant = client.get(
            f"/api/v1/ai-systems/{system_id}/transparency-assurance",
            headers=_headers(tenant_b, "auditor"),
        )
        assert cross_tenant.status_code == 404
        tenant_b_summary = client.get(
            "/api/v1/transparency-assurance",
            headers=_headers(tenant_b, "auditor"),
        )
        assert tenant_b_summary.status_code == 200
        assert tenant_b_summary.json()["systems"] == []

        viewer_read = client.get(
            "/api/v1/transparency-assurance",
            headers=_headers(tenant_a, "viewer"),
        )
        assert viewer_read.status_code == 403
        editor_write = client.put(
            f"/api/v1/ai-systems/{system_id}/transparency-assurance",
            headers=_headers(tenant_a, "editor"),
            json=_assessment_payload(expected_version=1),
        )
        assert editor_write.status_code == 403


def test_verified_review_requires_a_future_review_boundary() -> None:
    body = _assessment_payload()
    body["control_owner"] = None
    with pytest.raises(ValidationError, match="control_owner"):
        AITransparencyAssessmentUpsert.model_validate(body)

    body = _assessment_payload()
    body["review_due_at_utc"] = None
    with pytest.raises(ValidationError, match="review_due_at_utc"):
        AITransparencyAssessmentUpsert.model_validate(body)

    body = _assessment_payload()
    body["review_due_at_utc"] = datetime(2026, 7, 19, tzinfo=UTC).isoformat()
    with pytest.raises(ValidationError, match="cannot be before"):
        AITransparencyAssessmentUpsert.model_validate(body)


def test_transparency_migration_creates_normalized_tables_and_is_idempotent() -> None:
    migration_engine = create_engine("sqlite+pysqlite:///:memory:")
    AISystemTable.__table__.create(migration_engine)

    assert migration.apply(migration_engine) is True
    assert migration.apply(migration_engine) is False
    table_names = set(inspect(migration_engine).get_table_names())
    assert "ai_transparency_assessments" in table_names
    assert "ai_transparency_controls" in table_names
