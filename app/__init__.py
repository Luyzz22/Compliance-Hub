from __future__ import annotations

import os

__all__ = ["__version__"]

__version__ = "0.1.0"

_TELEMETRY_FLAGS = (
    "HAYSTACK_TELEMETRY_ENABLED",
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_TRACING",
)
_PRODUCTION_EXTERNAL_TELEMETRY_CONFIGURATION = (
    "LANGSMITH_API_KEY",
    "LANGSMITH_ENDPOINT",
    "LANGCHAIN_API_KEY",
    "LANGCHAIN_ENDPOINT",
    "POSTHOG_API_KEY",
    "POSTHOG_HOST",
)
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _enforce_dependency_telemetry_boundary() -> None:
    """Disable dependency telemetry before Haystack/LangGraph can be imported.

    Haystack enables its optional PostHog telemetry unless the environment variable is
    explicitly false. LangGraph can load LangSmith tracing configuration during imports.
    Package initialisation is the earliest reliable application boundary: startup and
    lifespan checks run after dependency modules may already have been imported.
    """

    environment = os.getenv("COMPLIANCEHUB_ENV", "dev").strip().lower()
    production = environment in {"prod", "production"}
    for name in _TELEMETRY_FLAGS:
        configured = os.getenv(name)
        enabled = configured is not None and configured.strip().lower() in _TRUE_VALUES
        if production and enabled:
            raise RuntimeError(f"{name} must be false in production")
        os.environ.setdefault(name, "false")
    if production:
        for name in _PRODUCTION_EXTERNAL_TELEMETRY_CONFIGURATION:
            if os.getenv(name, "").strip():
                raise RuntimeError(f"{name} is forbidden in production")


_enforce_dependency_telemetry_boundary()
