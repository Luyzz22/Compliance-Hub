"""Transport-level response hardening for the FastAPI service."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

Receive = Callable[..., Awaitable[Any]]
Send = Callable[..., Awaitable[Any]]
ASGIApp = Callable[[dict[str, Any], Receive, Send], Awaitable[Any]]


class SecurityHeadersMiddleware:
    """Add security headers without buffering streaming responses."""

    def __init__(self, app: ASGIApp, *, production: bool = False) -> None:
        self.app = app
        self.production = production

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Receive,
        send: Send,
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def send_hardened(message: dict[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                existing = {key.lower() for key, _ in headers}
                desired = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"no-referrer",
                    b"permissions-policy": (
                        b"camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
                        b"browsing-topics=()"
                    ),
                    b"cross-origin-opener-policy": b"same-origin",
                    b"cross-origin-resource-policy": b"same-site",
                }
                if self.production:
                    desired[b"strict-transport-security"] = (
                        b"max-age=63072000; includeSubDomains; preload"
                    )
                    desired[b"content-security-policy"] = (
                        b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
                        b"form-action 'none'"
                    )
                for key, value in desired.items():
                    if key not in existing:
                        headers.append((key, value))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_hardened)
