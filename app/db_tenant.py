"""Async SQLAlchemy session for RLS-scoped tenants (parity URL selection with sync ``app.db``)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth_dependencies import get_auth_context
from app.db import get_database_url
from app.security import AuthContext

#: PostgreSQL runtime parameter evaluated by the tenant-isolation RLS policies.
#: Must stay in sync with ``db/postgres/migrations/*_rls.sql``.
TENANT_GUC = "compliancehub.tenant_id"


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


async def get_async_db(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Open an async session bound to the authenticated tenant.

    The tenant is taken exclusively from the verified ``AuthContext`` (session token or
    tenant-scoped API key). Client-supplied headers are never trusted here: the value is
    written into a PostgreSQL session variable that RLS policies evaluate, so accepting
    an unverified header would be a cross-tenant bypass.

    Fails closed — without an authenticated tenant no session is handed out.

    Usage in FastAPI endpoints::

        session: AsyncSession = Depends(get_async_db)
    """
    tenant_id = str(auth.tenant_id or "").strip()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No authenticated tenant context",
        )

    async with AsyncSessionLocal() as session:
        if async_engine.dialect.name == "postgresql":
            await session.execute(
                text("SELECT set_config(:guc, :tid, true)"),
                {"guc": TENANT_GUC, "tid": tenant_id},
            )
        yield session
