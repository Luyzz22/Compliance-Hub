"""Fail-closed request and daily limits for governed LLM usage."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.db import SessionLocal
from app.llm_models import LLMDataClass, LLMProvider, LLMResponse, LLMTaskType
from app.services import llm_client
from app.services.llm_router import LLMRouter
from app.services.llm_usage_policy import LLMUsagePolicyExceeded, current_llm_usage_policy


def _enable_azure_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_CHAT_ASSISTANT", "true")
    monkeypatch.setenv("COMPLIANCEHUB_LLM_ASSUME_AZURE_EU", "true")
    monkeypatch.setenv("COMPLIANCEHUB_LLM_PREFER_AZURE", "true")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-enterprise")
    monkeypatch.setenv("AZURE_OPENAI_AUTH", "managed_identity")


def test_usage_policy_rejects_invalid_numeric_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_LLM_DAILY_CALL_LIMIT", "unbounded")

    with pytest.raises(llm_client.LLMConfigurationError, match="must be an integer"):
        current_llm_usage_policy()


def test_router_enforces_prompt_character_limit_before_provider_egress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_azure_chat(monkeypatch)
    monkeypatch.setenv("COMPLIANCEHUB_LLM_MAX_PROMPT_CHARACTERS", "256")
    provider_called = False

    def fake_call(*args: object, **kwargs: object) -> LLMResponse:
        nonlocal provider_called
        provider_called = True
        return LLMResponse(
            text="unexpected",
            provider=LLMProvider.AZURE_OPENAI,
            model_id="gpt-enterprise",
        )

    router = LLMRouter(call_model_fn=fake_call)
    with pytest.raises(LLMUsagePolicyExceeded, match="character limit"):
        router.route_and_call(
            LLMTaskType.CHAT_ASSISTANT,
            "x" * 257,
            "usage-prompt-limit",
            data_class=LLMDataClass.PUBLIC,
            required_provider=LLMProvider.AZURE_OPENAI,
        )

    assert provider_called is False


def test_router_enforces_daily_call_limit_before_second_provider_egress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_azure_chat(monkeypatch)
    monkeypatch.setenv("COMPLIANCEHUB_LLM_DAILY_CALL_LIMIT", "1")
    monkeypatch.setenv("COMPLIANCEHUB_LLM_DAILY_TOKEN_LIMIT", "5000")
    tenant_id = f"usage-daily-{uuid.uuid4().hex}"
    provider_calls = 0

    def fake_call(
        provider: LLMProvider,
        model_id: str,
        prompt: str,
        **kwargs: object,
    ) -> LLMResponse:
        nonlocal provider_calls
        provider_calls += 1
        return LLMResponse(
            text="synthetic result",
            provider=provider,
            model_id=model_id,
            input_tokens_est=4,
            output_tokens_est=8,
        )

    session = SessionLocal()
    try:
        router = LLMRouter(session=session, call_model_fn=fake_call)
        router.route_and_call(
            LLMTaskType.CHAT_ASSISTANT,
            "synthetic governance scenario",
            tenant_id,
            data_class=LLMDataClass.PUBLIC,
            required_provider=LLMProvider.AZURE_OPENAI,
        )
        with pytest.raises(LLMUsagePolicyExceeded, match="call budget"):
            router.route_and_call(
                LLMTaskType.CHAT_ASSISTANT,
                "second synthetic scenario",
                tenant_id,
                data_class=LLMDataClass.PUBLIC,
                required_provider=LLMProvider.AZURE_OPENAI,
            )
    finally:
        session.close()

    assert provider_calls == 1


def test_daily_usage_reservation_is_atomic_across_sessions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_azure_chat(monkeypatch)
    monkeypatch.setenv("COMPLIANCEHUB_LLM_DAILY_CALL_LIMIT", "1")
    monkeypatch.setenv("COMPLIANCEHUB_LLM_DAILY_TOKEN_LIMIT", "5000")
    tenant_id = f"usage-concurrent-{uuid.uuid4().hex}"

    def reserve_once() -> bool:
        session = SessionLocal()
        try:
            router = LLMRouter(
                session=session,
                call_model_fn=lambda provider, model_id, prompt, **kwargs: LLMResponse(
                    text="synthetic result",
                    provider=provider,
                    model_id=model_id,
                    input_tokens_est=4,
                    output_tokens_est=8,
                ),
            )
            router.route_and_call(
                LLMTaskType.CHAT_ASSISTANT,
                "concurrent synthetic scenario",
                tenant_id,
                data_class=LLMDataClass.PUBLIC,
                required_provider=LLMProvider.AZURE_OPENAI,
            )
            return True
        except LLMUsagePolicyExceeded:
            return False
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=6) as executor:
        accepted = list(executor.map(lambda _: reserve_once(), range(6)))

    assert accepted.count(True) == 1
    assert accepted.count(False) == 5


def test_required_provider_prevents_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_azure_chat(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    attempted: list[LLMProvider] = []

    def fake_call(
        provider: LLMProvider,
        model_id: str,
        prompt: str,
        **kwargs: object,
    ) -> LLMResponse:
        attempted.append(provider)
        raise RuntimeError("synthetic provider failure")

    router = LLMRouter(call_model_fn=fake_call)
    with pytest.raises(RuntimeError, match="provider failure"):
        router.route_and_call(
            LLMTaskType.CHAT_ASSISTANT,
            "synthetic scenario",
            "usage-required-provider",
            data_class=LLMDataClass.PUBLIC,
            required_provider=LLMProvider.AZURE_OPENAI,
        )

    assert attempted == [LLMProvider.AZURE_OPENAI]
