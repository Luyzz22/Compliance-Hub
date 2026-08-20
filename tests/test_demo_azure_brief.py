"""Azure-only executive brief for the immutable synthetic demo workspace."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.demo_models import DemoAzureBriefResponse, DemoAzureBriefScenario
from app.llm_models import LLMProvider, LLMResponse
from app.main import app
from app.repositories.tenant_registry import TenantRegistryRepository
from app.services import demo_azure_brief

client = TestClient(app)


def _create_tenant(*, is_demo: bool, demo_playground: bool = False) -> str:
    tenant_id = f"azure-demo-{uuid.uuid4().hex}"
    session = SessionLocal()
    try:
        TenantRegistryRepository(session).create(
            tenant_id=tenant_id,
            display_name="Synthetic Azure Demo",
            industry="Synthetic",
            country="DE",
            nis2_scope="in_scope",
            ai_act_scope="in_scope",
            is_demo=is_demo,
            demo_playground=demo_playground,
        )
    finally:
        session.close()
    return tenant_id


def _configure_demo(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    certificate = tmp_path / "azure-client.pem"
    certificate.write_text("synthetic-certificate-material")
    certificate.chmod(0o400)
    values = {
        "COMPLIANCEHUB_DEMO_AZURE_INFERENCE_ENABLED": "true",
        "COMPLIANCEHUB_DEMO_SYNTHETIC_ONLY_ATTESTED": "true",
        "COMPLIANCEHUB_FEATURE_DEMO_MODE": "true",
        "COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS": "true",
        "COMPLIANCEHUB_FEATURE_LLM_ENABLED": "true",
        "COMPLIANCEHUB_FEATURE_LLM_CHAT_ASSISTANT": "true",
        "COMPLIANCEHUB_LLM_PREFER_AZURE": "true",
        "COMPLIANCEHUB_LLM_ASSUME_AZURE_EU": "true",
        "COMPLIANCEHUB_LLM_PII_MODE": "block",
        "COMPLIANCEHUB_SOVEREIGNTY_MODE": "standard_dach",
        "COMPLIANCEHUB_LLM_DAILY_CALL_LIMIT": "20",
        "COMPLIANCEHUB_LLM_DAILY_TOKEN_LIMIT": "50000",
        "COMPLIANCEHUB_LLM_MAX_PROMPT_CHARACTERS": "12000",
        "COMPLIANCEHUB_LLM_MAX_OUTPUT_TOKENS": "800",
        "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
        "AZURE_OPENAI_DEPLOYMENT": "gpt-enterprise",
        "AZURE_OPENAI_AUTH": "client_certificate",
        "AZURE_TENANT_ID": "synthetic-tenant-id",
        "AZURE_CLIENT_ID": "synthetic-client-id",
        "AZURE_CLIENT_CERTIFICATE_PATH": str(certificate),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)


def test_service_uses_only_fixed_synthetic_prompt_and_azure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _configure_demo(monkeypatch, tmp_path)
    tenant_id = _create_tenant(is_demo=True)
    captured: dict[str, object] = {}

    def fake_guardrailed_call(
        session,
        task_type,
        prompt,
        routed_tenant_id,
        **kwargs,
    ) -> LLMResponse:
        captured.update(
            prompt=prompt,
            tenant_id=routed_tenant_id,
            required_provider=kwargs["required_provider"],
        )
        return LLMResponse(
            text=(
                '{"title":"Synthetisches Governance-Briefing",'
                '"executive_summary":"Das synthetische Szenario benötigt vor einer '
                'Freigabe nachvollziehbare Nachweise und eine dokumentierte Prüfung.",'
                '"recommended_actions":["Offene Evidence-Referenzen fachlich prüfen",'
                '"Verantwortliche Rollen nachvollziehbar bestätigen",'
                '"Vier-Augen-Freigabe dokumentiert abschließen"],'
                '"human_review_note":"Eine benannte Fachperson muss die Aussagen vor jeder '
                'weiteren Verwendung prüfen."}'
            ),
            provider=LLMProvider.AZURE_OPENAI,
            model_id="gpt-enterprise",
            input_tokens_est=50,
            output_tokens_est=90,
        )

    monkeypatch.setattr(
        demo_azure_brief,
        "guardrailed_route_and_call_sync",
        fake_guardrailed_call,
    )
    session = SessionLocal()
    try:
        result = demo_azure_brief.generate_demo_azure_brief(
            session,
            tenant_id=tenant_id,
            scenario=DemoAzureBriefScenario.governance_release_gate,
        )
    finally:
        session.close()

    assert result.synthetic_data_only is True
    assert result.data_class == "public"
    assert captured["tenant_id"] == tenant_id
    assert captured["required_provider"] == LLMProvider.AZURE_OPENAI
    assert "ausschließlich synthetischen" in str(captured["prompt"])


def test_endpoint_allows_fixed_action_for_read_only_demo_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = _create_tenant(is_demo=True)

    def fake_generate(session, *, tenant_id: str, scenario: DemoAzureBriefScenario):
        return DemoAzureBriefResponse(
            scenario=scenario,
            provider="azure_openai",
            model_id="gpt-enterprise",
            title="Synthetisches Governance-Briefing",
            executive_summary=(
                "Das synthetische Szenario zeigt einen kontrollierten Azure-Demopfad."
            ),
            recommended_actions=[
                "Evidence-Referenzen fachlich prüfen",
                "Verantwortliche Rollen schriftlich bestätigen",
                "Vier-Augen-Freigabe nachvollziehbar abschließen",
            ],
            human_review_note="Eine Fachperson prüft das Ergebnis vor jeder Verwendung.",
            input_tokens_est=40,
            output_tokens_est=70,
        )

    monkeypatch.setattr("app.main.generate_demo_azure_brief", fake_generate)
    response = client.post(
        "/api/v1/demo/azure-governance-brief",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": tenant_id},
        json={"scenario": "governance_release_gate"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["synthetic_data_only"] is True


def test_endpoint_rejects_free_text_fields() -> None:
    tenant_id = _create_tenant(is_demo=True)
    response = client.post(
        "/api/v1/demo/azure-governance-brief",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": tenant_id},
        json={
            "scenario": "supplier_risk",
            "prompt": "Dieser freie Kundentext darf Azure nicht erreichen.",
        },
    )

    assert response.status_code == 422


def test_service_rejects_non_demo_and_playground_tenants(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    _configure_demo(monkeypatch, tmp_path)
    for tenant_id in (
        _create_tenant(is_demo=False),
        _create_tenant(is_demo=True, demo_playground=True),
    ):
        session = SessionLocal()
        try:
            with pytest.raises(PermissionError, match="read-only demo tenant"):
                demo_azure_brief.generate_demo_azure_brief(
                    session,
                    tenant_id=tenant_id,
                    scenario=DemoAzureBriefScenario.incident_readiness,
                )
        finally:
            session.close()


def test_service_is_disabled_by_default() -> None:
    tenant_id = _create_tenant(is_demo=True)
    session = SessionLocal()
    try:
        with pytest.raises(PermissionError, match="disabled"):
            demo_azure_brief.generate_demo_azure_brief(
                session,
                tenant_id=tenant_id,
                scenario=DemoAzureBriefScenario.supplier_risk,
            )
    finally:
        session.close()
