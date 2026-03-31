"""FastAPI-facing helpers: enforce OPA-backed action policies."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.policy.opa_client import evaluate_action_policy
from app.policy.user_context import UserPolicyContext


def enforce_action_policy(
    action: str,
    user: UserPolicyContext,
    *,
    risk_score: float = 0.5,
) -> None:
    """
    Build OPA input and raise HTTP 403 when the policy denies the action.

    API error text stays English; user-facing product copy remains German elsewhere.
    """
    payload = {
        "tenant_id": user.tenant_id,
        "user_role": user.user_role,
        "action": action,
        "risk_score": float(risk_score),
    }
    decision = evaluate_action_policy(payload)
    if decision.allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Action denied by policy",
    )
