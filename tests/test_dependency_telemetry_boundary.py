"""Early process boundary for optional third-party dependency telemetry."""

from __future__ import annotations

import os

import pytest

import app


def test_dependency_telemetry_defaults_to_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("HAYSTACK_TELEMETRY_ENABLED", "LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "dev")

    app._enforce_dependency_telemetry_boundary()

    assert os.environ["HAYSTACK_TELEMETRY_ENABLED"] == "false"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "false"
    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_dependency_telemetry_cannot_be_enabled_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("HAYSTACK_TELEMETRY_ENABLED", "true")

    with pytest.raises(RuntimeError, match="must be false in production"):
        app._enforce_dependency_telemetry_boundary()


@pytest.mark.parametrize(
    "variable",
    [
        "LANGCHAIN_TRACING_V2",
        "LANGSMITH_TRACING",
        "LANGSMITH_API_KEY",
        "LANGSMITH_ENDPOINT",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_ENDPOINT",
        "POSTHOG_API_KEY",
        "POSTHOG_HOST",
    ],
)
def test_external_dependency_telemetry_is_rejected_before_imports_in_production(
    monkeypatch: pytest.MonkeyPatch,
    variable: str,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv(variable, "true" if variable.endswith(("TRACING", "TRACING_V2")) else "set")

    with pytest.raises(RuntimeError, match=variable):
        app._enforce_dependency_telemetry_boundary()
