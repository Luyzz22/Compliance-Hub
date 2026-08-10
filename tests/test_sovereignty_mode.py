"""Deployment sovereignty mode: provider ceiling, startup verification, claim surface."""

from __future__ import annotations

import pytest

from app import sovereignty
from app.llm_models import LLMProvider, LLMTaskType
from app.services.llm_router import filter_candidates, preference_chain
from app.services.tenant_llm_policy import default_tenant_llm_policy


@pytest.fixture(autouse=True)
def _clear_mode_cache():
    sovereignty.current_mode.cache_clear()
    yield
    sovereignty.current_mode.cache_clear()


def _set_mode(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_SOVEREIGNTY_MODE", mode)
    sovereignty.current_mode.cache_clear()


def test_default_mode_authorises_no_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    An unconfigured deployment must not assert a posture nobody selected.

    Defaulting to ``standard_dach`` would look safer but would have the runtime authorise
    statements like "Betrieb in EU-Rechenzentren" that nothing guarantees — and would cut
    off model providers a running deployment may depend on.
    """
    monkeypatch.delenv("COMPLIANCEHUB_SOVEREIGNTY_MODE", raising=False)
    sovereignty.current_mode.cache_clear()
    assert sovereignty.current_mode() is sovereignty.SovereigntyMode.UNRESTRICTED
    assert sovereignty.current_profile().permitted_claims_de == ()


def test_default_mode_does_not_break_existing_provider_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Upgrading without choosing a mode must not silently disable LLM routing."""
    monkeypatch.delenv("COMPLIANCEHUB_SOVEREIGNTY_MODE", raising=False)
    monkeypatch.setenv("COMPLIANCEHUB_LLM_US_CLOUD_OK", "true")
    sovereignty.current_mode.cache_clear()

    assert sovereignty.verify_startup_configuration() == []
    chain = ["claude", "openai", "azure_openai", "gemini", "llama"]
    assert sovereignty.filter_llm_provider_chain(chain) == chain


def test_unknown_mode_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_mode(monkeypatch, "eu_sovereign_ish")
    with pytest.raises(sovereignty.SovereigntyConfigurationError):
        sovereignty.current_mode()


@pytest.mark.parametrize(
    ("mode", "forbidden"),
    [
        ("standard_dach", {"openai", "claude", "gemini"}),
        ("eu_sovereign", {"openai", "claude", "gemini", "azure_openai"}),
        ("strict_sovereign", {"openai", "claude", "gemini", "azure_openai"}),
    ],
)
def test_forbidden_providers_are_removed_not_reordered(
    monkeypatch: pytest.MonkeyPatch, mode: str, forbidden: set[str]
) -> None:
    """
    A chain that merely *prefers* an EU provider still falls back to a US one on error.

    That is precisely the situation an EU-residency commitment has to rule out, so the
    forbidden providers must be absent from the chain, not merely ranked lower.
    """
    _set_mode(monkeypatch, mode)
    chain = ["claude", "openai", "azure_openai", "gemini", "llama"]
    result = sovereignty.filter_llm_provider_chain(chain)
    assert not (set(result) & forbidden)
    assert "llama" in result


def test_router_never_selects_us_provider_in_eu_sovereign_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end through the router's candidate filter, not just the helper."""
    _set_mode(monkeypatch, "eu_sovereign")
    # Tenant policy deliberately as permissive as it can be: the deployment mode is a
    # ceiling no tenant setting may lift.
    policy = default_tenant_llm_policy("tenant-sovereign")
    policy.allowed_providers = list(LLMProvider)
    monkeypatch.setenv("COMPLIANCEHUB_LLM_US_CLOUD_OK", "true")
    monkeypatch.setenv("COMPLIANCEHUB_LLM_ASSUME_CLAUDE_EU", "true")
    monkeypatch.setenv("COMPLIANCEHUB_LLM_ASSUME_AZURE_EU", "true")

    ordered = preference_chain(LLMTaskType.LEGAL_REASONING, policy)
    candidates = filter_candidates(policy, ordered)

    us_providers = {LLMProvider.OPENAI, LLMProvider.CLAUDE, LLMProvider.GEMINI}
    assert not (set(candidates) & us_providers)


def test_startup_verification_rejects_forbidden_env(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_mode(monkeypatch, "eu_sovereign")
    monkeypatch.setenv("COMPLIANCEHUB_LLM_US_CLOUD_OK", "true")
    with pytest.raises(sovereignty.SovereigntyConfigurationError, match="US_CLOUD_OK"):
        sovereignty.verify_startup_configuration()


def test_startup_verification_passes_for_clean_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_mode(monkeypatch, "eu_sovereign")
    for name in ("COMPLIANCEHUB_LLM_US_CLOUD_OK", "COMPLIANCEHUB_LLM_ASSUME_CLAUDE_EU"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    assert sovereignty.verify_startup_configuration() == []


def test_strict_mode_forbids_azure_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_mode(monkeypatch, "strict_sovereign")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    violations = sovereignty.verify_startup_configuration(raise_on_error=False)
    assert any("AZURE_OPENAI_ENDPOINT" in v for v in violations)


def test_unrestricted_mode_permits_no_residency_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The honest escape hatch must not authorise any residency statement."""
    _set_mode(monkeypatch, "unrestricted")
    payload = sovereignty.public_profile_payload()
    assert payload["permitted_claims_de"] == []
    assert "EU-Hosting" in payload["forbidden_claims_de"]


@pytest.mark.parametrize(
    "mode", ["unrestricted", "standard_dach", "eu_sovereign", "strict_sovereign"]
)
def test_no_mode_permits_the_phrase_dsgvo_konform(
    monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    """
    "DSGVO-konform" is a property of the whole socio-technical system, never of software
    alone, so no operating mode may ever authorise it.
    """
    _set_mode(monkeypatch, mode)
    profile = sovereignty.current_profile()
    permitted = " ".join(profile.permitted_claims_de).lower()
    assert "dsgvo-konform" not in permitted


def test_profile_payload_is_json_serialisable(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    _set_mode(monkeypatch, "standard_dach")
    json.dumps(sovereignty.public_profile_payload())
