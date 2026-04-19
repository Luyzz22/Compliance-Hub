"""Async SQLAlchemy session for JWT/RLS tenants (parity URL selection with sync ``app.db``)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import get_database_url


def _async_database_url() -> str:
    """Map sync driver URLs from ``COMPLIANCEHUB_DB_URL`` to async-capable dialects."""
    url = get_database_url()
    if url.startswith("sqlite+pysqlite"):
        return url.replace("sqlite+pysqlite", "sqlite+aiosqlite", 1)
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


async_engine = create_async_engine(
    _async_database_url(),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)


async def get_async_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Öffnet eine async DB-Session und setzt SET LOCAL app.current_tenant
    aus dem JWT (via TenantMiddleware) – damit greift PostgreSQL RLS automatisch.

    Verwendung in FastAPI-Endpoints:
        session: AsyncSession = Depends(get_async_db)
    """
    async with AsyncSessionLocal() as session:
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            await session.execute(
                text("SET LOCAL app.current_tenant = :tid"),
                {"tid": str(tenant_id)},
            )
        yield session
