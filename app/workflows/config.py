"""Temporal connection settings (local dev or Temporal Cloud)."""

from __future__ import annotations

import os


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
    if os.getenv("TEMPORAL_TLS", "").strip().lower() in ("1", "true", "yes", "on"):
        return True
    return temporal_api_key() is not None
