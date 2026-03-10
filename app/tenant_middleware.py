from __future__ import annotations

import logging
from typing import Callable

import jwt
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

from .config import settings

ALGORITHM = "HS256"


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Extrahiert tenant_id aus dem Supabase-JWT (oder X-Tenant-Id Header)
    und setzt sie als request.state.tenant_id für die DB-Session.

    Reihenfolge:
      1. Bearer-Token im Authorization-Header (Supabase JWT)
      2. X-Tenant-Id Header (Service-to-Service, z.B. n8n-Workflows)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tenant_id: str | None = None

        # 1) JWT aus Authorization-Header
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
            try:
                payload = jwt.decode(
                    token,
                    settings.SUPABASE_JWT_SECRET,
                    algorithms=[ALGORITHM],
                    options={"verify_aud": False},
                )
                tenant_id = payload.get("tenant_id")
            except jwt.ExpiredSignatureError:
                logger.warning("TenantMiddleware: JWT expired")
            except jwt.InvalidTokenError as e:
                logger.warning("TenantMiddleware: JWT invalid – %s", e)

        # 2) Fallback: expliziter Header (z.B. für Service-to-Service)
        if not tenant_id:
            tenant_id = request.headers.get("x-tenant-id")

        request.state.tenant_id = tenant_id
        return await call_next(request)
