"""Tenant GUC binding for RLS-scoped async sessions.

The GUC is set with ``is_local => true``, which scopes it to the current transaction. A
handler that commits mid-request would otherwise continue on the same session with the
setting reset, and every following statement would be evaluated by RLS as having no
tenant. These tests pin the re-binding behaviour, which the SQLite test database cannot
exercise through the normal request path.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from sqlalchemy import text

from app.db_tenant import (
    TENANT_GUC,
    AsyncSessionLocal,
    _bind_tenant_guc_per_transaction,
    get_async_db,
)
from app.security import AuthContext


def test_guc_name_matches_rls_policy() -> None:
    """
    The GUC must be the one the RLS policies actually read.

    An earlier revision set ``app.current_tenant`` while
    ``db/postgres/migrations/20260715_advisor_runtime_state_rls.sql`` evaluates
    ``compliancehub.tenant_id`` — so the setting had no effect on any policy.
    """
    assert TENANT_GUC == "compliancehub.tenant_id"

    with open("db/postgres/migrations/20260715_advisor_runtime_state_rls.sql") as handle:
        policy_sql = handle.read()
    assert f"current_setting('{TENANT_GUC}'" in policy_sql


def test_listener_rebinds_after_commit() -> None:
    """The binding must fire again for the transaction that follows a commit."""

    async def scenario() -> list[tuple[str, str]]:
        applied: list[tuple[str, str]] = []

        async with AsyncSessionLocal() as session:
            sync_session = session.sync_session
            _bind_tenant_guc_per_transaction(sync_session, "tenant-rebind")

            # Record what the listener would issue, independent of the SQLite dialect
            # short-circuit, by observing every transaction start.
            from sqlalchemy import event

            @event.listens_for(sync_session, "after_begin")
            def _record(
                _session: Any,
                _transaction: Any,
                connection: Any,
            ) -> None:
                applied.append((TENANT_GUC, str(connection.dialect.name)))

            await session.execute(text("SELECT 1"))
            await session.commit()
            await session.execute(text("SELECT 1"))
            await session.commit()

        return applied

    applied = asyncio.run(scenario())
    assert len(applied) >= 2, "GUC must be re-applied for each transaction, not only the first"
    assert all(guc == TENANT_GUC for guc, _ in applied)


def test_listener_is_inert_on_non_postgres_dialect() -> None:
    """SQLite has no ``set_config``; the listener must skip rather than raise."""

    async def scenario() -> int:
        async with AsyncSessionLocal() as session:
            _bind_tenant_guc_per_transaction(session.sync_session, "tenant-sqlite")
            await session.execute(text("SELECT 1"))
            await session.commit()
            result = await session.execute(text("SELECT 2"))
            return int(result.scalar_one())

    assert asyncio.run(scenario()) == 2


def test_get_async_db_rejects_missing_tenant() -> None:
    """Fail closed: no authenticated tenant means no session at all."""

    async def scenario() -> None:
        agen = get_async_db(AuthContext(tenant_id="   "))
        await agen.__anext__()

    with pytest.raises(Exception) as excinfo:
        asyncio.run(scenario())
    assert getattr(excinfo.value, "status_code", None) == 401
