"""Temporal connection settings for an optional self-hosted worker plane."""

from __future__ import annotations

import os

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


class TemporalConfigurationError(RuntimeError):
    """Raised when the optional Temporal integration is not explicitly enabled."""


def temporal_enabled() -> bool:
    """Temporal is opt-in so an unused orchestration SDK cannot create egress."""

    return os.getenv("COMPLIANCEHUB_TEMPORAL_ENABLED", "false").strip().lower() in _TRUE_VALUES


def require_temporal_enabled() -> None:
    if not temporal_enabled():
        raise TemporalConfigurationError("Temporal workflow orchestration is disabled")


def temporal_address() -> str:
    return os.getenv("TEMPORAL_ADDRESS", "localhost:7233").strip()


def temporal_namespace() -> str:
    return os.getenv("TEMPORAL_NAMESPACE", "default").strip()


def temporal_task_queue() -> str:
    return os.getenv("TEMPORAL_TASK_QUEUE", "compliancehub-main").strip()


def temporal_api_key() -> str | None:
    raw = os.getenv("TEMPORAL_API_KEY", "").strip()
    return raw or None


def temporal_tls_enabled() -> bool:
    if os.getenv("TEMPORAL_TLS", "").strip().lower() in _TRUE_VALUES:
        return True
    return temporal_api_key() is not None
