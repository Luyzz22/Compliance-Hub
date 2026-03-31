"""KI-Assist: NIS2-KPI-Vorschläge, Explain, Action-Drafts (gemockter LLM)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.ai_governance_action_models import (
    ActionDraftRequirementInput,
    AIGovernanceActionDraftRequest,
)
from app.ai_system_models import (
    AIActCategory,
    AISystem,
    AISystemCriticality,
    AISystemRiskLevel,
    AISystemStatus,
    DataSensitivity,
)
from app.db import SessionLocal
from app.explain_models import ExplainRequest
from app.llm_models import LLMProvider, LLMResponse
from app.main import app
from app.nis2_kritis_models import Nis2KritisKpiSuggestionRequest
from app.repositories.usage_events import UsageEventRepository
from app.services.ai_action_drafts import generate_action_drafts
from app.services.ai_explain import explain_kpi_or_alert
from app.services.nis2_kritis_ai_assist import generate_nis2_kpi_suggestions

client = TestClient(app)
API_KEY = "test-api-key"
TENANT = "llm-gov-assist-tenant"


def _system(tid: str = TENANT) -> AISystem:
    return AISystem(
        id="sys-kpi-ai",
        tenant_id=tid,
        name="Demo HR Bot",
        description="Internes HR-Chatbot mit personenbezogenen Daten.",
        business_unit="HR",
        risk_level=AISystemRiskLevel.high,
        ai_act_category=AIActCategory.high_risk,
        gdpr_dpia_required=True,
        criticality=AISystemCriticality.high,
        data_sensitivity=DataSensitivity.confidential,
        has_incident_runbook=True,
        has_supplier_risk_register=False,
        has_backup_runbook=True,
        status=AISystemStatus.active,
    )


def test_generate_nis2_kpi_suggestions_parses_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_KPI_SUGGESTIONS", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test")

    payload = {
        "suggestions": [
            {
                "kpi_type": "INCIDENT_RESPONSE_MATURITY",
                "suggested_value_percent": 80,
                "confidence": 0.85,
                "rationale": "Runbooks vorhanden.",
            },
            {
                "kpi_type": "SUPPLIER_RISK_COVERAGE",
                "suggested_value_percent": 40,
                "confidence": 0.7,
                "rationale": "Register fehlt.",
            },
            {
                "kpi_type": "OT_IT_SEGREGATION",
                "suggested_value_percent": 55,
                "confidence": 0.6,
                "rationale": "Teilweise Segmentierung.",
            },
        ],
    }

    def fake_route(self, task_type, prompt, tenant_id, **kwargs):  # noqa: ANN001
        return LLMResponse(
            text=json.dumps(payload),
            provider=LLMProvider.GEMINI,
            model_id="m",
        )

    monkeypatch.setattr(
        "app.services.llm_router.LLMRouter.route_and_call",
        fake_route,
    )

    req = Nis2KritisKpiSuggestionRequest(
        ai_system_id="sys-kpi-ai",
        free_text="Wir haben Incident-Runbooks und Backups dokumentiert.",
    )
    out = generate_nis2_kpi_suggestions(
        _system(),
        req,
        TENANT,
        session=None,
        existing_kpis_summary=[],
    )
    assert len(out.suggestions) == 3
    assert out.suggestions[0].kpi_type.value == "INCIDENT_RESPONSE_MATURITY"


def test_explain_kpi_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_EXPLAIN", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")

    payload = {
        "title": "NIS2 Incident Readiness",
        "summary": "Anteil Systeme mit dokumentierten Runbooks.",
        "why_it_matters": ["NIS2 verlangt Melde- und Reaktionsfähigkeit."],
        "suggested_actions": ["Runbooks pflegen."],
    }

    def fake_route(self, task_type, prompt, tenant_id, **kwargs):  # noqa: ANN001
        return LLMResponse(text=json.dumps(payload), provider=LLMProvider.OPENAI, model_id="m")

    monkeypatch.setattr(
        "app.services.llm_router.LLMRouter.route_and_call",
        fake_route,
    )

    er = explain_kpi_or_alert(
        ExplainRequest(
            kpi_key="nis2_incident_readiness_ratio",
            current_value=72.0,
            value_is_percent=True,
        ),
        TENANT,
        session=None,
    )
    assert "NIS2" in er.title or "Incident" in er.title


def test_action_drafts_empty_requirements_raises() -> None:
    with pytest.raises(ValueError, match="requirements"):
        generate_action_drafts(
            AIGovernanceActionDraftRequest(ai_system_id=None, requirements=[]),
            TENANT,
            session=None,
        )


def test_action_drafts_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ACTION_DRAFTS", "true")
    monkeypatch.setenv("CLAUDE_API_KEY", "k")

    payload = {
        "drafts": [
            {
                "title": "Risikomanagement dokumentieren",
                "description": "Prozess für Art. 9 etablieren.",
                "framework": "EU_AI_ACT",
                "reference": "Art. 9",
                "priority": "high",
                "suggested_role": "CISO",
            },
            {
                "title": "Logging prüfen",
                "description": "Art. 12 Nachvollziehbarkeit.",
                "framework": "EU_AI_ACT",
                "reference": "Art. 12",
                "priority": "medium",
                "suggested_role": "AI Owner",
            },
        ],
    }

    def fake_route(self, task_type, prompt, tenant_id, **kwargs):  # noqa: ANN001
        return LLMResponse(text=json.dumps(payload), provider=LLMProvider.CLAUDE, model_id="m")

    monkeypatch.setattr(
        "app.services.llm_router.LLMRouter.route_and_call",
        fake_route,
    )

    body = AIGovernanceActionDraftRequest(
        ai_system_id=None,
        requirements=[
            ActionDraftRequirementInput(
                framework="EU_AI_ACT",
                reference="Art. 9",
                gap_description="Kein dokumentiertes Risk Management.",
            ),
        ],
    )
    out = generate_action_drafts(body, TENANT, session=None)
    assert len(out.drafts) == 2


def test_kpi_suggestions_api_forbidden_without_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "false")
    r = client.post(
        "/api/v1/ai-systems/x/nis2-kritis-kpi-suggestions",
        headers={"x-api-key": API_KEY, "x-tenant-id": TENANT},
        json={"free_text": "12345678901 Kontext genug."},
    )
    assert r.status_code == 403


def test_kpi_suggestion_logs_usage_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_KPI_SUGGESTIONS", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("COMPLIANCEHUB_USAGE_TRACKING", "true")

    sid = "llm-kpi-suggest-sys"
    create = client.post(
        "/api/v1/ai-systems",
        headers={"x-api-key": API_KEY, "x-tenant-id": TENANT},
        json={
            "id": sid,
            "name": "LLM KPI Test",
            "description": "Test",
            "business_unit": "IT",
            "risk_level": AISystemRiskLevel.high.value,
            "ai_act_category": AIActCategory.high_risk.value,
            "gdpr_dpia_required": True,
            "criticality": AISystemCriticality.medium.value,
            "data_sensitivity": DataSensitivity.internal.value,
            "has_incident_runbook": True,
            "has_supplier_risk_register": False,
            "has_backup_runbook": True,
        },
    )
    assert create.status_code == 200, create.text

    payload = {
        "suggestions": [
            {
                "kpi_type": "INCIDENT_RESPONSE_MATURITY",
                "suggested_value_percent": 10,
                "confidence": 0.5,
                "rationale": "a",
            },
            {
                "kpi_type": "SUPPLIER_RISK_COVERAGE",
                "suggested_value_percent": 20,
                "confidence": 0.5,
                "rationale": "b",
            },
            {
                "kpi_type": "OT_IT_SEGREGATION",
                "suggested_value_percent": 30,
                "confidence": 0.5,
                "rationale": "c",
            },
        ],
    }

    def fake_route(self, task_type, prompt, tenant_id, **kwargs):  # noqa: ANN001
        return LLMResponse(text=json.dumps(payload), provider=LLMProvider.GEMINI, model_id="m")

    monkeypatch.setattr(
        "app.services.llm_router.LLMRouter.route_and_call",
        fake_route,
    )

    s = SessionLocal()
    try:
        r = client.post(
            f"/api/v1/ai-systems/{sid}/nis2-kritis-kpi-suggestions",
            headers={"x-api-key": API_KEY, "x-tenant-id": TENANT},
            json={"free_text": "12345678901 ausreichend lang."},
        )
        assert r.status_code == 200, r.text
        repo = UsageEventRepository(s)
        from datetime import UTC, datetime, timedelta

        since = datetime.now(UTC) - timedelta(minutes=2)
        counts = repo.count_by_type_since(
            TENANT,
            ["llm_kpi_suggestion_requested"],
            since=since,
        )
        assert counts.get("llm_kpi_suggestion_requested", 0) >= 1
    finally:
        s.close()
