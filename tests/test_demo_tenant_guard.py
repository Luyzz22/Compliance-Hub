"""Unit-Tests: zentrale Demo-/Playground-Schreibpolicy (ohne HTTP)."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import engine
from app.demo_tenant_guard import (
    DEMO_TENANT_READONLY_CODE,
    demo_readonly_blocks_mutations,
    raise_if_demo_tenant_readonly,
)
from app.models_db import TenantDB


def _tid() -> str:
    return f"ut-guard-{uuid.uuid4().hex[:10]}"


def test_demo_readonly_blocks_when_demo_not_playground() -> None:
    tid = _tid()
    with Session(engine) as s:
        s.add(
            TenantDB(
                id=tid,
                display_name="G",
                industry="IT",
                country="DE",
                is_demo=True,
                demo_playground=False,
            ),
        )
        s.commit()
        assert demo_readonly_blocks_mutations(s, tid) is True


def test_demo_playground_allows_mutations_without_strict_env() -> None:
    tid = _tid()
    with Session(engine) as s:
        s.add(
            TenantDB(
                id=tid,
                display_name="G",
                industry="IT",
                country="DE",
                is_demo=True,
                demo_playground=True,
            ),
        )
        s.commit()
        assert demo_readonly_blocks_mutations(s, tid) is False


def test_demo_playground_blocked_when_env_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS", "true")
    tid = _tid()
    with Session(engine) as s:
        s.add(
            TenantDB(
                id=tid,
                display_name="G",
                industry="IT",
                country="DE",
                is_demo=True,
                demo_playground=True,
            ),
        )
        s.commit()
        assert demo_readonly_blocks_mutations(s, tid) is True


def test_unknown_tenant_not_blocked() -> None:
    with Session(engine) as s:
        assert demo_readonly_blocks_mutations(s, "no-such-tenant-xyz") is False


def test_raise_if_demo_includes_stable_code() -> None:
    tid = _tid()
    with Session(engine) as s:
        s.add(
            TenantDB(
                id=tid,
                display_name="G",
                industry="IT",
                country="DE",
                is_demo=True,
                demo_playground=False,
            ),
        )
        s.commit()
        with pytest.raises(HTTPException) as exc_info:
            raise_if_demo_tenant_readonly(s, tid)
        assert exc_info.value.status_code == 403
        body = exc_info.value.detail
        assert isinstance(body, dict)
        assert body["code"] == DEMO_TENANT_READONLY_CODE
        assert "read-only" in body["message"].lower()
        assert "hint" in body
        assert "write" in body["hint"].lower()
