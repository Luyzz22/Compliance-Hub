"""
Light-weight OpenTelemetry tracing (swappable exporters: console, none, test memory).

Env:
- COMPLIANCEHUB_OTEL_ENABLED: ``1``/``true`` to register a real TracerProvider (default: enabled).
- COMPLIANCEHUB_OTEL_SERVICE_NAME: default ``compliancehub-api``.
- COMPLIANCEHUB_ENVIRONMENT: ``dev`` | ``stage`` | ``prod`` (span resource attribute).
- COMPLIANCEHUB_OTEL_CONSOLE_EXPORTER: ``1`` to attach ConsoleSpanProcessor (dev only).
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Generator, Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from opentelemetry import context, trace
from opentelemetry.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

_TRACER_NAME = "compliancehub"
_CONFIGURED = False
_TEST_MEMORY_EXPORTER: Any | None = None
_TEXTMAP = TraceContextTextMapPropagator()


def _parse_env_bool(key: str, default: bool = False) -> bool:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def service_name() -> str:
    return os.getenv("COMPLIANCEHUB_OTEL_SERVICE_NAME", "compliancehub-api").strip()


def deployment_environment() -> str:
    return os.getenv("COMPLIANCEHUB_ENVIRONMENT", "dev").strip().lower()


def configure_telemetry(*, force: bool = False) -> None:
    """Idempotent SDK registration; noop provider when disabled."""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return
    _CONFIGURED = True
    if not _parse_env_bool("COMPLIANCEHUB_OTEL_ENABLED", True):
        logger.info("OpenTelemetry tracing disabled (COMPLIANCEHUB_OTEL_ENABLED=false)")
        return
    resource = Resource.create(
        {
            "service.name": service_name(),
            "deployment.environment": deployment_environment(),
        },
    )
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    if _parse_env_bool("COMPLIANCEHUB_OTEL_CONSOLE_EXPORTER"):
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        logger.info("OpenTelemetry console span exporter enabled")
    logger.info(
        "OpenTelemetry TracerProvider configured service=%s env=%s",
        service_name(),
        deployment_environment(),
    )


def configure_telemetry_test_memory_exporter() -> Any:
    """
    Attach in-memory export to the active SDK ``TracerProvider`` (singleton).

    OpenTelemetry forbids replacing ``TracerProvider`` after startup; tests that import
    ``app.main`` first rely on ``configure_telemetry()`` in lifespan, then we add a
    ``SimpleSpanProcessor`` here. Returns the shared ``InMemorySpanExporter``.
    """
    global _CONFIGURED, _TEST_MEMORY_EXPORTER
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    if _TEST_MEMORY_EXPORTER is not None:
        _TEST_MEMORY_EXPORTER.clear()
        return _TEST_MEMORY_EXPORTER

    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)
    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        current.add_span_processor(processor)
        _TEST_MEMORY_EXPORTER = exporter
        _CONFIGURED = True
        return exporter

    resource = Resource.create(
        {
            "service.name": "compliancehub-api-test",
            "deployment.environment": "test",
        },
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _TEST_MEMORY_EXPORTER = exporter
    _CONFIGURED = True
    return exporter


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(_TRACER_NAME)


def get_trace_context_for_log_fields() -> dict[str, str]:
    """Hex trace_id / span_id for joining structured logs to traces (no PII)."""
    span = trace.get_current_span()
    sc = span.get_span_context()
    if not sc.is_valid:
        return {}
    return {
        "trace_id": format(sc.trace_id, "032x"),
        "span_id": format(sc.span_id, "016x"),
    }


def _norm_attrs(attrs: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in attrs.items():
        if v is None:
            continue
        if isinstance(v, (bool, int, float, str)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


@contextmanager
def start_span(name: str, **attrs: Any) -> Generator[Span, None, None]:
    """Start a span; records exceptions; no-op-like when tracer is not recording."""
    tracer = get_tracer()
    with tracer.start_as_current_span(name, attributes=_norm_attrs(attrs)) as span:
        try:
            yield span
        except Exception as exc:
            if span.is_recording():
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.record_exception(exc)
            raise


def record_event(name: str, **attrs: Any) -> None:
    """Add a named event on the current span (OTel ``add_event``)."""
    span = trace.get_current_span()
    if not span.is_recording():
        return
    span.add_event(name, attributes=_norm_attrs(attrs))


def inject_trace_carrier(carrier: dict[str, str]) -> None:
    """Inject W3C traceparent into ``carrier`` (mutates dict)."""
    _TEXTMAP.inject(carrier)


@contextmanager
def attach_trace_carrier(carrier: Mapping[str, str] | None) -> Iterator[None]:
    """
    Context manager: continue trace from W3C ``traceparent`` in carrier (Temporal worker).
    """
    if not carrier or not str(carrier.get("traceparent", "")).strip():
        yield
        return
    cap = {k: str(v) for k, v in carrier.items() if v is not None}
    ctx = _TEXTMAP.extract(cap, context=context.get_current())
    token = context.attach(ctx)
    try:
        yield
    finally:
        context.detach(token)


def extract_trace_from_headers(headers: Mapping[str, str]) -> Context:
    """Build a Context from incoming HTTP headers (lowercase keys ok)."""
    carrier = {k.lower(): v for k, v in headers.items()}
    return _TEXTMAP.extract(carrier, context=context.get_current())


def attach_context(ctx: Context) -> object:
    return context.attach(ctx)


def detach_context(token: object) -> None:
    context.detach(token)


def new_correlation_id() -> str:
    return str(uuid.uuid4())
