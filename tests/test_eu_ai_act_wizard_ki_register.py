"""EU AI Act Wizard, KI-Register, Export/Reporting – Unit + Integration Tests."""

from __future__ import annotations

import json
import uuid
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from app.eu_ai_act_wizard_engine import run_wizard
from app.eu_ai_act_wizard_models import (
    AIActRiskCategory,
    AIActRole,
    WizardQuestionnaireRequest,
)
from app.main import app
from tests.conftest import _headers

client = TestClient(app)


# ── Wizard Engine Unit Tests ─────────────────────────────────────────────


def test_wizard_prohibited_social_scoring() -> None:
    q = WizardQuestionnaireRequest(
        ai_system_id="test-prohibited",
        involves_social_scoring=True,
    )
    result = run_wizard(q)
    assert result.risk_category == AIActRiskCategory.UNACCEPTABLE
    assert "Art. 5" in result.applicable_articles[0].article
    assert result.confidence_score == 1.0


def test_wizard_gpai_model() -> None:
    q = WizardQuestionnaireRequest(
        ai_system_id="test-gpai",
        is_general_purpose_ai=True,
        gpai_has_systemic_risk=True,
    )
    result = run_wizard(q)
    assert result.risk_category == AIActRiskCategory.GPAI
    assert any("Art. 55" in a.article for a in result.applicable_articles)


def test_wizard_high_risk_annex_i_provider() -> None:
    q = WizardQuestionnaireRequest(
        ai_system_id="test-annex-i",
        role=AIActRole.provider,
        is_product_or_safety_component=True,
        covered_by_eu_harmonisation_legislation=True,
        requires_third_party_conformity=True,
        legislation_reference="MDR (EU) 2017/745",
    )
    result = run_wizard(q)
    assert result.risk_category == AIActRiskCategory.HIGH_RISK
    assert result.role == AIActRole.provider
    assert any("Art. 9" in a.article for a in result.applicable_articles)
    assert any("Art. 72" in a.article for a in result.applicable_articles)


def test_wizard_high_risk_annex_iii_deployer() -> None:
    q = WizardQuestionnaireRequest(
        ai_system_id="test-annex-iii",
        role=AIActRole.deployer,
        use_case_domain="employment",
        profiles_natural_persons=True,
    )
    result = run_wizard(q)
    assert result.risk_category == AIActRiskCategory.HIGH_RISK
    assert result.role == AIActRole.deployer
    assert any("Art. 29" in a.article for a in result.applicable_articles)


def test_wizard_annex_iii_exception_no_profiling() -> None:
    q = WizardQuestionnaireRequest(
        ai_system_id="test-exception",
        use_case_domain="education",
        is_narrow_procedural_task=True,
        profiles_natural_persons=False,
    )
    result = run_wizard(q)
    assert result.risk_category == AIActRiskCategory.LOW


def test_wizard_transparency_chatbot() -> None:
    q = WizardQuestionnaireRequest(
        ai_system_id="test-chatbot",
        is_chatbot_or_conversational=True,
    )
    result = run_wizard(q)
    assert result.risk_category == AIActRiskCategory.LIMITED
    assert any("Art. 50" in a.article for a in result.applicable_articles)


def test_wizard_minimal_risk() -> None:
    q = WizardQuestionnaireRequest(ai_system_id="test-minimal")
    result = run_wizard(q)
    assert result.risk_category == AIActRiskCategory.LOW


def test_wizard_role_obligations_importer() -> None:
    q = WizardQuestionnaireRequest(
        ai_system_id="test-importer",
        role=AIActRole.importer,
        is_product_or_safety_component=True,
        covered_by_eu_harmonisation_legislation=True,
        requires_third_party_conformity=True,
    )
    result = run_wizard(q)
    assert result.risk_category == AIActRiskCategory.HIGH_RISK
    assert "Importer" in result.obligations_summary


# ── Wizard API Integration Test ──────────────────────────────────────────


def test_wizard_api_endpoint() -> None:
    r = client.post(
        "/api/v1/eu-ai-act/wizard",
        json={
            "ai_system_id": "api-test-system",
            "role": "provider",
            "use_case_domain": "essential_services",
            "profiles_natural_persons": True,
        },
        headers=_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["risk_category"] == "HIGH_RISK"
    assert data["role"] == "provider"
    assert len(data["applicable_articles"]) > 0


# ── KI-Register API Tests ───────────────────────────────────────────────


def _create_system_with_ki_fields(sid: str) -> None:
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": sid,
            "name": "KI Register Test System",
            "description": "Test for KI register fields.",
            "business_unit": "Compliance",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "test@example.com",
            "criticality": "high",
            "data_sensitivity": "confidential",
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
            "intended_purpose": "Automated credit scoring for retail.",
            "training_data_provenance": "Internal DWH 2020-2024.",
            "fria_reference": "FRIA-2025-001",
            "provider_name": "FinTech GmbH",
            "deployer_name": "Test Corp",
        },
        headers=_headers(),
    )


def test_ki_register_list() -> None:
    sid = f"ki-reg-list-{uuid.uuid4().hex[:8]}"
    _create_system_with_ki_fields(sid)
    r = client.get("/api/v1/ki-register", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == _headers()["x-tenant-id"]
    assert data["total"] >= 1
    found = [s for s in data["items"] if s["ai_system_id"] == sid]
    assert len(found) == 1
    assert found[0]["intended_purpose"] == "Automated credit scoring for retail."
    assert found[0]["provider_name"] == "FinTech GmbH"


def test_ki_register_patch() -> None:
    sid = f"ki-reg-patch-{uuid.uuid4().hex[:8]}"
    _create_system_with_ki_fields(sid)
    r = client.patch(
        f"/api/v1/ki-register/{sid}",
        json={
            "intended_purpose": "Updated purpose",
            "fria_reference": "FRIA-2025-002",
        },
        headers=_headers(),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "updated"

    # Verify via list
    r2 = client.get("/api/v1/ki-register", headers=_headers())
    found = [s for s in r2.json()["items"] if s["ai_system_id"] == sid]
    assert found[0]["intended_purpose"] == "Updated purpose"
    assert found[0]["fria_reference"] == "FRIA-2025-002"


def test_ki_register_patch_not_found() -> None:
    r = client.patch(
        "/api/v1/ki-register/nonexistent-system",
        json={"intended_purpose": "x"},
        headers=_headers(),
    )
    assert r.status_code == 404


# ── Export API Tests ─────────────────────────────────────────────────────


def test_ki_register_export_json() -> None:
    sid = f"ki-reg-exp-json-{uuid.uuid4().hex[:8]}"
    _create_system_with_ki_fields(sid)
    r = client.get("/api/v1/ki-register/export?fmt=json", headers=_headers())
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/json"
    data = json.loads(r.text)
    assert data["tenant_id"] == _headers()["x-tenant-id"]
    assert len(data["systems"]) >= 1


def test_ki_register_export_xml() -> None:
    sid = f"ki-reg-exp-xml-{uuid.uuid4().hex[:8]}"
    _create_system_with_ki_fields(sid)
    r = client.get("/api/v1/ki-register/export?fmt=xml", headers=_headers())
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/xml"
    root = ET.fromstring(r.text)
    assert root.tag == "KIRegisterExport"
    systems = root.find("systems")
    assert systems is not None
    assert len(systems.findall("system")) >= 1


# ── Board Aggregation Test ───────────────────────────────────────────────


def test_ki_register_board_aggregation() -> None:
    sid = f"ki-reg-board-{uuid.uuid4().hex[:8]}"
    _create_system_with_ki_fields(sid)
    r = client.get("/api/v1/ki-register/board-aggregation", headers=_headers())
    assert r.status_code == 200
    data = r.json()
    assert data["tenant_id"] == _headers()["x-tenant-id"]
    assert data["total_systems"] >= 1
    assert "open_actions_count" in data
    assert "pms_overdue_count" in data


# ── Seed Data Test ───────────────────────────────────────────────────────


def test_seed_eu_ai_act_demo_idempotent() -> None:
    r1 = client.post("/api/internal/eu-ai-act/seed-demo", headers=_headers())
    assert r1.status_code == 200
    r1.json()  # verify parseable
    # Second call should be idempotent (no new systems)
    r2 = client.post("/api/internal/eu-ai-act/seed-demo", headers=_headers())
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["created_systems"] == 0


# ── KI-Register fields in AI System CRUD ─────────────────────────────────


def test_ai_system_create_with_ki_fields() -> None:
    sid = f"ki-fields-create-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/api/v1/ai-systems",
        json={
            "id": sid,
            "name": "KI Fields Test",
            "description": "Test",
            "business_unit": "IT",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "intended_purpose": "Automated decision for loans",
            "training_data_provenance": "Internal customer data 2020-2024",
            "fria_reference": "FRIA-2025-TEST",
            "provider_name": "Test AI Provider",
            "deployer_name": "Test Corp",
            "provider_responsibilities": "Model training and validation",
            "deployer_responsibilities": "Human oversight, Art. 14",
        },
        headers=_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["intended_purpose"] == "Automated decision for loans"
    assert data["provider_name"] == "Test AI Provider"
    assert data["fria_reference"] == "FRIA-2025-TEST"
    assert data["pms_status"] == "pending"


def test_ai_system_update_ki_fields() -> None:
    sid = f"ki-fields-update-{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": sid,
            "name": "Update Test",
            "description": "Test",
            "business_unit": "IT",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
        },
        headers=_headers(),
    )
    r = client.patch(
        f"/api/v1/ai-systems/{sid}",
        json={
            "intended_purpose": "New purpose",
            "provider_name": "New Provider GmbH",
        },
        headers=_headers(),
    )
    assert r.status_code == 200
    assert r.json()["intended_purpose"] == "New purpose"
    assert r.json()["provider_name"] == "New Provider GmbH"
