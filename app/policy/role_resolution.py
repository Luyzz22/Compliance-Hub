"""Resolve OPA `user_role` from optional trusted header, env, or route default."""

from __future__ import annotations

import os

ALLOWED_OPA_ROLES = frozenset(
    {
        "advisor",
        "auditor",
        "compliance_officer",
        "integration_admin",
        "it_ops",
        "platform_admin",
        "tenant_admin",
        "tenant_user",
        "viewer",
    },
)

# Env var names (documented in docs/architecture/wave1-opa-langgraph-guardrails.md)
ENV_ROLE_BOARD_REPORT = "COMPLIANCEHUB_OPA_ROLE_BOARD_REPORT"
ENV_ROLE_READINESS_EXPLAIN = "COMPLIANCEHUB_OPA_ROLE_READINESS_EXPLAIN"
ENV_ROLE_LANGGRAPH_OAMI_POC = "COMPLIANCEHUB_OPA_ROLE_LANGGRAPH_OAMI_POC"
ENV_ROLE_ADVISOR_TENANT_REPORT = "COMPLIANCEHUB_OPA_ROLE_ADVISOR_TENANT_REPORT"
ENV_ROLE_ADVISOR_RAG = "COMPLIANCEHUB_OPA_ROLE_ADVISOR_RAG"
ENV_ROLE_AI_EVIDENCE = "COMPLIANCEHUB_OPA_ROLE_AI_EVIDENCE"


def _env_bool(key: str) -> bool:
    raw = os.getenv(key, "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _normalize(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def resolve_opa_role_for_policy(
    *,
    header_value: str | None,
    env_var_name: str,
    default: str,
) -> str:
    """
    Order when ``COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER`` is enabled:
    ``x-opa-user-role`` header (allowlist only), else env ``env_var_name``, else ``default``.

    When trust is disabled: env, then default. Invalid values are ignored (fall through).
    """
    if _env_bool("COMPLIANCEHUB_OPA_TRUST_CLIENT_ROLE_HEADER"):
        hv = _normalize(header_value)
        if hv in ALLOWED_OPA_ROLES:
            return hv

    ev = _normalize(os.getenv(env_var_name))
    if ev in ALLOWED_OPA_ROLES:
        return ev

    dv = _normalize(default) or "tenant_user"
    if dv in ALLOWED_OPA_ROLES:
        return dv
    return "tenant_user"
