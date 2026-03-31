"""HTTP client for Open Policy Agent (OPA) decision API."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str = Field(default="", max_length=2000)


def _truthy_env(key: str) -> bool:
    raw = os.getenv(key)
    if raw is None or not str(raw).strip():
        return False
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _opa_url() -> str:
    return os.getenv("OPA_URL", "").strip()


def _opa_policy_path() -> str:
    raw = os.getenv("OPA_POLICY_PATH", "/v1/data/compliancehub/allow_action").strip()
    return raw if raw.startswith("/") else f"/{raw}"


def evaluate_action_policy(input_payload: dict[str, Any]) -> PolicyDecision:
    """
    POST {OPA_URL}{OPA_POLICY_PATH} with body {"input": ...}; expects boolean `result`.

    When OPA_URL is unset, decisions default to allow (local dev / gradual rollout).
    Set COMPLIANCEHUB_OPA_STRICT_MISSING=1 to deny when OPA is not configured.
    """
    base = _opa_url()
    if not base:
        if _truthy_env("COMPLIANCEHUB_OPA_STRICT_MISSING"):
            return PolicyDecision(allowed=False, reason="opa_not_configured")
        logger.debug("OPA_URL unset; allowing action (opa_disabled)")
        return PolicyDecision(allowed=True, reason="opa_disabled")

    path = _opa_policy_path()
    url = f"{base.rstrip('/')}{path}"
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(url, json={"input": input_payload})
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("opa_request_failed url=%s err=%s", url, exc)
        return PolicyDecision(allowed=False, reason="opa_unreachable")
    except ValueError as exc:
        logger.warning("opa_invalid_json url=%s err=%s", url, exc)
        return PolicyDecision(allowed=False, reason="opa_invalid_response")

    result = body.get("result")
    if isinstance(result, dict) and "allow_action" in result:
        inner = result.get("allow_action")
        allowed = bool(inner)
    else:
        allowed = bool(result)
    if allowed:
        return PolicyDecision(allowed=True, reason="opa_allow")
    return PolicyDecision(allowed=False, reason="opa_deny")
