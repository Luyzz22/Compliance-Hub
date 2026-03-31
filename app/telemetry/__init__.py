"""Cross-cutting observability (OpenTelemetry-style tracing, structured joins with logs)."""

from __future__ import annotations

from app.telemetry.tracing import (
    configure_telemetry,
    configure_telemetry_test_memory_exporter,
    get_trace_context_for_log_fields,
    record_event,
    start_span,
)

__all__ = [
    "configure_telemetry",
    "configure_telemetry_test_memory_exporter",
    "get_trace_context_for_log_fields",
    "record_event",
    "start_span",
]
