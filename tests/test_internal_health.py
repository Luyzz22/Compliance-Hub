"""Gated internal deep-health endpoint (monitoring agents)."""

import pytest
from fastapi.testclient import TestClient

from app import sovereignty
from app.llm_models import LLMProvider
from app.main import app
from app.policy.opa_client import PolicyDecision

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_health_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "INTERNAL_HEALTH_API_KEY",
        "INTERNAL_HEALTH_API_KEY_FILE",
        "INTERNAL_HEALTH_ALLOWED_IPS",
        "INTERNAL_HEALTH_AI_PROVIDER_SIGNAL",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        "app.services.internal_health_core.evaluate_action_policy",
        lambda _payload: PolicyDecision(allowed=False, reason="opa_deny"),
    )
    sovereignty.current_mode.cache_clear()
    yield
    sovereignty.current_mode.cache_clear()


def test_internal_health_requires_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTERNAL_HEALTH_API_KEY", raising=False)
    monkeypatch.delenv("INTERNAL_HEALTH_API_KEY_FILE", raising=False)
    resp = client.get(
        "/api/internal/health",
        headers={"X-HEALTH-KEY": "ignored"},
    )
    assert resp.status_code == 503


def test_internal_health_rejects_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    resp = client.get("/api/internal/health")
    assert resp.status_code == 401


def test_internal_health_rejects_wrong_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    resp = client.get(
        "/api/internal/health",
        headers={"X-HEALTH-KEY": "wrong"},
    )
    assert resp.status_code == 401


def test_internal_health_ok_with_valid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    monkeypatch.setenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "up")
    resp = client.get(
        "/api/internal/health",
        headers={"X-HEALTH-KEY": "test-health-secret"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["app"] == "up"
    assert body["db"] == "up"
    assert body["policy_engine"] == "up"
    assert body["external_ai_provider"] == "up"
    assert "timestamp" in body


def test_internal_health_ip_allowlist_blocks_unknown_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    monkeypatch.setenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "up")
    monkeypatch.setenv("INTERNAL_HEALTH_ALLOWED_IPS", "203.0.113.10")
    resp = client.get(
        "/api/internal/health",
        headers={"X-HEALTH-KEY": "test-health-secret"},
    )
    assert resp.status_code == 403


def test_internal_health_ip_allowlist_allows_testclient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    monkeypatch.setenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "up")
    monkeypatch.setenv("INTERNAL_HEALTH_ALLOWED_IPS", "testclient")
    resp = client.get(
        "/api/internal/health",
        headers={"X-HEALTH-KEY": "test-health-secret"},
    )
    assert resp.status_code == 200


def test_readiness_fails_when_the_configured_ai_path_is_down(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    monkeypatch.setenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "down")

    resp = client.get(
        "/api/internal/readiness",
        headers={"X-HEALTH-KEY": "test-health-secret"},
    )

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Deployment is not ready"


def test_readiness_accepts_degraded_optional_ai_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    monkeypatch.setenv("INTERNAL_HEALTH_AI_PROVIDER_SIGNAL", "degraded")

    resp = client.get(
        "/api/internal/readiness",
        headers={"X-HEALTH-KEY": "test-health-secret"},
    )

    assert resp.status_code == 200
    assert resp.json()["db"] == "up"


def test_standard_dach_health_ignores_forbidden_direct_us_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_SOVEREIGNTY_MODE", "standard_dach")
    monkeypatch.setenv("OPENAI_API_KEY", "configured-but-forbidden")
    sovereignty.current_mode.cache_clear()

    from app.services.internal_health_core import _external_ai_provider_signal

    assert _external_ai_provider_signal() == "down"


def test_standard_dach_health_accepts_private_local_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_SOVEREIGNTY_MODE", "standard_dach")
    monkeypatch.setenv("LLAMA_BASE_URL", "http://local-llm:8000")
    monkeypatch.setenv("COMPLIANCEHUB_LLAMA_PRIVATE_HOSTS", "local-llm")
    sovereignty.current_mode.cache_clear()

    from app.services.internal_health_core import _external_ai_provider_signal

    assert _external_ai_provider_signal() == "up"


def test_standard_dach_health_rejects_public_local_model_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_SOVEREIGNTY_MODE", "standard_dach")
    monkeypatch.setenv("LLAMA_BASE_URL", "https://models.example.com")
    sovereignty.current_mode.cache_clear()

    from app.services.internal_health_core import _external_ai_provider_signal

    assert _external_ai_provider_signal() == "down"


def test_standard_dach_health_requires_azure_eu_attestation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_FEATURE_LLM_ENABLED", "true")
    monkeypatch.setenv("COMPLIANCEHUB_SOVEREIGNTY_MODE", "standard_dach")
    sovereignty.current_mode.cache_clear()
    monkeypatch.setattr(
        "app.services.internal_health_core.is_provider_configured",
        lambda provider: provider is LLMProvider.AZURE_OPENAI,
    )

    from app.services.internal_health_core import _external_ai_provider_signal

    assert _external_ai_provider_signal() == "down"
    monkeypatch.setenv("COMPLIANCEHUB_LLM_ASSUME_AZURE_EU", "true")
    assert _external_ai_provider_signal() == "up"


def test_readiness_fails_when_policy_engine_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTERNAL_HEALTH_API_KEY", "test-health-secret")
    monkeypatch.setattr(
        "app.services.internal_health_core.evaluate_action_policy",
        lambda _payload: PolicyDecision(allowed=False, reason="opa_unreachable"),
    )

    resp = client.get(
        "/api/internal/readiness",
        headers={"X-HEALTH-KEY": "test-health-secret"},
    )

    assert resp.status_code == 503
