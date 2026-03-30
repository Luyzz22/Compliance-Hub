"""Tests: OPA user_role resolution (env + optional trusted header)."""

from __future__ import annotations

import pytest

from app.policy.role_resolution import (
    ENV_ROLE_BOARD_REPORT,
    ENV_ROLE_READINESS_EXPLAIN,
    resolve_opa_role_for_policy,
)


def test_resolve_prefers_header_when_trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER", "true")
    r = resolve_opa_role_for_policy(
        header_value="tenant_admin",
        env_var_name=ENV_ROLE_READINESS_EXPLAIN,
        default="tenant_user",
    )
    assert r == "tenant_admin"


def test_resolve_ignores_header_when_not_trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER", raising=False)
    monkeypatch.setenv(ENV_ROLE_READINESS_EXPLAIN, "tenant_user")
    r = resolve_opa_role_for_policy(
        header_value="tenant_admin",
        env_var_name=ENV_ROLE_READINESS_EXPLAIN,
        default="tenant_user",
    )
    assert r == "tenant_user"


def test_resolve_env_overrides_default_when_untrusted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER", raising=False)
    monkeypatch.setenv(ENV_ROLE_BOARD_REPORT, "advisor")
    r = resolve_opa_role_for_policy(
        header_value=None,
        env_var_name=ENV_ROLE_BOARD_REPORT,
        default="tenant_admin",
    )
    assert r == "advisor"


def test_resolve_invalid_env_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER", raising=False)
    monkeypatch.setenv(ENV_ROLE_BOARD_REPORT, "not_a_real_role")
    r = resolve_opa_role_for_policy(
        header_value=None,
        env_var_name=ENV_ROLE_BOARD_REPORT,
        default="tenant_admin",
    )
    assert r == "tenant_admin"


def test_resolve_invalid_header_falls_through_when_trusted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER", "true")
    monkeypatch.setenv(ENV_ROLE_READINESS_EXPLAIN, "tenant_user")
    r = resolve_opa_role_for_policy(
        header_value="superuser",
        env_var_name=ENV_ROLE_READINESS_EXPLAIN,
        default="tenant_admin",
    )
    assert r == "tenant_user"
