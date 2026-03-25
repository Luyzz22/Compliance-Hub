"""EU-AI-Act-Dokumentation: API, Versionierung, Export, LLM-Draft (gemockt)."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.llm_models import LLMProvider, LLMResponse
from app.main import app
from app.services.ai_act_docs_ai_assist import generate_ai_act_doc_draft
from tests.conftest import _headers

client = TestClient(app)


def _post_high_risk(sid: str) -> None:
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": sid,
            "name": "HR High Risk Doc",
            "description": "Test system for AI Act documentation endpoints.",
            "business_unit": "HR",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "owner@example.com",
            "criticality": "high",
            "data_sensitivity": "internal",
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
        },
        headers=_headers(),
    )


def test_ai_act_docs_forbidden_when_feature_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_ACT_DOCS", "false")
    sid = f"ai-doc-off-{uuid.uuid4().hex[:8]}"
    _post_high_risk(sid)
    r = client.get(
        f"/api/v1/ai-systems/{sid}/ai-act-docs",
        headers=_headers(),
    )
    assert r.status_code == 403


def test_ai_act_docs_rejects_non_high_risk(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_ACT_DOCS", "true")
    low_id = f"ai-doc-low-{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/v1/ai-systems",
        json={
            "id": low_id,
            "name": "Low",
            "description": "Low risk",
            "business_unit": "Ops",
            "risk_level": "low",
            "ai_act_category": "minimal_risk",
            "gdpr_dpia_required": False,
            "criticality": "medium",
            "data_sensitivity": "internal",
            "has_incident_runbook": False,
            "has_supplier_risk_register": False,
            "has_backup_runbook": False,
        },
        headers=_headers(),
    )
    r = client.get(
        f"/api/v1/ai-systems/{low_id}/ai-act-docs",
        headers=_headers(),
    )
    assert r.status_code == 400


def test_ai_act_docs_list_upsert_version_export(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_ACT_DOCS", "true")
    sid = f"ai-doc-crud-{uuid.uuid4().hex[:8]}"
    _post_high_risk(sid)
    lst = client.get(
        f"/api/v1/ai-systems/{sid}/ai-act-docs",
        headers=_headers(),
    )
    assert lst.status_code == 200
    body = lst.json()
    assert body["ai_system_id"] == sid
    assert len(body["items"]) == 5
    assert body["items"][0]["section_key"] == "RISK_MANAGEMENT"

    u1 = client.post(
        f"/api/v1/ai-systems/{sid}/ai-act-docs/RISK_MANAGEMENT",
        headers=_headers(),
        json={"title": "RM v1", "content_markdown": "Alpha"},
    )
    assert u1.status_code == 200
    assert u1.json()["version"] == 1

    u2 = client.post(
        f"/api/v1/ai-systems/{sid}/ai-act-docs/RISK_MANAGEMENT",
        headers=_headers(),
        json={"title": "RM v2", "content_markdown": "Beta"},
    )
    assert u2.status_code == 200
    assert u2.json()["version"] == 2

    exp = client.get(
        f"/api/v1/ai-systems/{sid}/ai-act-docs/export",
        headers=_headers(),
    )
    assert exp.status_code == 200
    text = exp.text
    assert "AI-Act-Dokumentationssektionen" in text
    assert "RM v2" in text
    assert "Beta" in text


def test_ai_act_doc_draft_llm_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_LEGAL_REASONING", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_REPORT_ASSISTANT", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test")

    def fake_route(self, task_type, prompt, tenant_id, **kwargs):  # noqa: ANN001
        if "JSON" in prompt or "json" in prompt.lower():
            return LLMResponse(
                text=json.dumps(
                    {"title": "Draft Title", "content_markdown": "## Abschnitt\n\nInhalt."},
                ),
                provider=LLMProvider.GEMINI,
                model_id="m",
            )
        return LLMResponse(
            text="- Stichpunkt zu Risiko\n- Stichpunkt zu Daten",
            provider=LLMProvider.GEMINI,
            model_id="m",
        )

    monkeypatch.setattr(
        "app.services.llm_router.LLMRouter.route_and_call",
        fake_route,
    )

    from app.ai_act_doc_models import AIActDocSectionKey
    from app.ai_system_models import (
        AIActCategory,
        AISystem,
        AISystemCriticality,
        AISystemRiskLevel,
        AISystemStatus,
        DataSensitivity,
    )

    sid = f"ai-doc-llm-{uuid.uuid4().hex[:8]}"
    system = AISystem(
        id=sid,
        tenant_id="t1",
        name="Sys",
        description="Desc",
        business_unit="BU",
        risk_level=AISystemRiskLevel.high,
        ai_act_category=AIActCategory.high_risk,
        gdpr_dpia_required=True,
        criticality=AISystemCriticality.high,
        data_sensitivity=DataSensitivity.internal,
        has_incident_runbook=True,
        has_supplier_risk_register=False,
        has_backup_runbook=True,
        status=AISystemStatus.active,
    )
    out = generate_ai_act_doc_draft(
        system,
        AIActDocSectionKey.RISK_MANAGEMENT,
        "t1",
        session=None,
        classification=None,
        nis2_kpis=[],
        actions_brief=[],
        evidence_file_count=0,
    )
    assert out.title == "Draft Title"
    assert "## Abschnitt" in out.content_markdown


def test_ai_act_docs_tenant_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_AI_ACT_DOCS", "true")
    sid = f"ai-doc-iso-{uuid.uuid4().hex[:8]}"
    _post_high_risk(sid)
    tid_b = f"ai-act-doc-tenant-b-{uuid.uuid4().hex[:6]}"
    h_b = {"x-api-key": "board-kpi-key", "x-tenant-id": tid_b}
    r = client.get(
        f"/api/v1/ai-systems/{sid}/ai-act-docs",
        headers=h_b,
    )
    assert r.status_code == 404
