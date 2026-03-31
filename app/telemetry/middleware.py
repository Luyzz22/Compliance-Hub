"""ASGI middleware: root HTTP span, W3C trace context, correlation id, tenant headers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from opentelemetry import context
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.telemetry.tracing import extract_trace_from_headers, get_tracer, new_correlation_id


class TelemetryMiddleware(BaseHTTPMiddleware):
    """
    One root span per request; propagates ``traceparent`` / ``tracestate``; sets
    ``http.*``, ``tenant_id`` (from ``x-tenant-id`` when present), ``user_role``,
    ``correlation_id``.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        trace_headers = {k.decode(): v.decode() for k, v in request.scope.get("headers", [])}
        ctx = extract_trace_from_headers(trace_headers)
        token = context.attach(ctx)
        tracer = get_tracer()
        route_path = request.scope.get("path", "") or ""
        method = request.method
        span_name = f"http {method} {route_path}"
        try:
            with tracer.start_as_current_span(span_name) as span:
                corr = request.headers.get("x-correlation-id") or new_correlation_id()
                if span.is_recording():
                    span.set_attribute("http.method", method)
                    span.set_attribute("http.target", route_path)
                    span.set_attribute("correlation_id", corr)
                    tid = request.headers.get("x-tenant-id")
                    if tid:
                        span.set_attribute("tenant_id", tid)
                    role = request.headers.get("x-opa-user-role")
                    if role:
                        span.set_attribute("user_role", role)
                response = await call_next(request)
                if span.is_recording():
                    span.set_attribute("http.status_code", response.status_code)
                response.headers["X-Correlation-ID"] = corr
                return response
        finally:
            context.detach(token)
