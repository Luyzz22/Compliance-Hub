"""LLM-Router: Policies, Residency, Fallbacks, Metadaten-Logging."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.feature_flags import FeatureFlag, is_feature_enabled
from app.llm_models import (
    CostSensitivity,
    DataResidencyPolicy,
    LLMProvider,
    LLMResponse,
    LLMTaskType,
    PublicApiPolicy,
)
from app.main import app
from app.repositories.llm_call_metadata import LLMCallMetadataRepository
from app.services import llm_client, tenant_llm_policy
from app.services.llm_router import LLMRouter, filter_candidates, preference_chain
from app.services.tenant_llm_policy import default_tenant_llm_policy

client = TestClient(app)


def test_llm_master_feature_defaults_off() -> None:
    assert is_feature_enabled(FeatureFlag.llm_enabled) is False


def test_preference_chain_legal_reasoning_claude_first() -> None:
    p = default_tenant_llm_policy("t1")
    chain = preference_chain(LLMTaskType.LEGAL_REASONING, p)
    assert chain[0] == LLMProvider.CLAUDE


def test_preference_chain_structured_output_openai_first() -> None:
    p = default_tenant_llm_policy("t1")
    chain = preference_chain(LLMTaskType.STRUCTURED_OUTPUT, p)
    assert chain[0] == LLMProvider.OPENAI


def test_cost_sensitivity_high_gemini_first_for_classification() -> None:
    p = default_tenant_llm_policy("t1")
    p = p.model_copy(update={"cost_sensitivity": CostSensitivity.HIGH})
    chain = preference_chain(LLMTaskType.CLASSIFICATION_TAGGING, p)
    assert chain[0] == LLMProvider.GEMINI


def test_filter_eu_only_keeps_llama_without_us_attestation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMPLIANCEHUB_LLM_ASSUME_CLAUDE_EU", raising=False)
    monkeypatch.delenv("COMPLIANCEHUB_LLM_US_CLOUD_OK", raising=False)
    monkeypatch.setenv("LLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    p = default_tenant_llm_policy("t1").model_copy(
        update={"data_residency": DataResidencyPolicy.EU_ONLY},
    )
    ordered = preference_chain(LLMTaskType.LEGAL_REASONING, p)
    c = filter_candidates(p, ordered)
    assert c == [LLMProvider.LLAMA]


def test_filter_on_prem_only_public_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    p = default_tenant_llm_policy("t1").model_copy(
        update={"public_api_policy": PublicApiPolicy.ON_PREM_ONLY},
    )
    ordered = preference_chain(LLMTaskType.CHAT_ASSISTANT, p)
    c = filter_candidates(p, ordered)
    assert c == [LLMProvider.LLAMA]


def test_router_skips_unconfigured_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_LEGAL_REASONING", "true")
    monkeypatch.delenv("CLAUDE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def fake_call(
        provider: LLMProvider,
        model_id: str,
        prompt: str,
        **kwargs: object,
    ) -> LLMResponse:
        return LLMResponse(text="ok", provider=provider, model_id=model_id)

    router = LLMRouter(session=None, call_model_fn=fake_call)
    resp = router.route_and_call(LLMTaskType.LEGAL_REASONING, "ping", "tenant-routing-1")
    assert resp.text == "ok"
    assert resp.provider == LLMProvider.OPENAI


def test_router_fallback_on_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_LEGAL_REASONING", "true")
    monkeypatch.setenv("CLAUDE_API_KEY", "k")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    def fake_call(
        provider: LLMProvider,
        model_id: str,
        prompt: str,
        **kwargs: object,
    ) -> LLMResponse:
        if provider == LLMProvider.CLAUDE:
            raise llm_client.LLMProviderHTTPError("upstream")
        return LLMResponse(text="fallback", provider=provider, model_id=model_id)

    router = LLMRouter(session=None, call_model_fn=fake_call)
    resp = router.route_and_call(LLMTaskType.LEGAL_REASONING, "ping", "tenant-routing-2")
    assert resp.provider == LLMProvider.OPENAI
    assert resp.text == "fallback"


def test_on_prem_sensitive_requires_llama_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.delenv("LLAMA_BASE_URL", raising=False)
    router = LLMRouter(session=None)
    with pytest.raises(llm_client.LLMConfigurationError, match="ON_PREM_SENSITIVE"):
        router.route_and_call(LLMTaskType.ON_PREM_SENSITIVE, "x", "t-prem")


def test_metadata_inserted_when_session_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_CLASSIFICATION_TAGGING", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key-for-routing")

    def fake_call(
        provider: LLMProvider,
        model_id: str,
        prompt: str,
        **kwargs: object,
    ) -> LLMResponse:
        return LLMResponse(text="abc", provider=provider, model_id=model_id)

    tid = "llm-meta-tenant"
    s = SessionLocal()
    try:
        router = LLMRouter(session=s, call_model_fn=fake_call)
        router.route_and_call(LLMTaskType.CLASSIFICATION_TAGGING, "hello-world", tid)
        repo = LLMCallMetadataRepository(s)
        since = datetime.now(UTC) - timedelta(minutes=5)
        assert repo.count_since(tid, since=since) >= 1
    finally:
        s.close()


def test_get_tenant_llm_policy_from_env_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "COMPLIANCEHUB_LLM_TENANT_POLICIES_JSON",
        json.dumps(
            {
                "tenant-pol-env": {
                    "allowed_providers": ["openai"],
                    "default_provider_by_task": {"legal_reasoning": "openai"},
                },
            },
        ),
    )
    p = tenant_llm_policy.get_tenant_llm_policy("tenant-pol-env", None)
    assert p.allowed_providers == [LLMProvider.OPENAI]
    assert p.default_provider_by_task[LLMTaskType.LEGAL_REASONING] == LLMProvider.OPENAI


def test_llm_invoke_forbidden_when_master_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "false")
    r = client.post(
        "/api/v1/llm/invoke",
        headers={"x-api-key": "board-kpi-key", "x-tenant-id": "llm-api-tenant"},
        json={"task_type": "chat_assistant", "prompt": "hi"},
    )
    assert r.status_code == 403
