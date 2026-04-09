"""Feature-gating enforcement middleware.

Provides a reusable FastAPI dependency ``require_plan`` that checks the
authenticated tenant's subscription plan against a feature matrix.
Returns HTTP 402 when the tenant's plan does not include the requested feature.

Trial subscriptions receive full Enterprise access for 14 days.
Expired trials are treated as having no active plan.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from enum import StrEnum

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth_dependencies import get_api_key_and_tenant
from app.db import get_session
from app.models_db import SubscriptionDB
from app.services.stripe_billing_service import PLAN_CATALOG

logger = logging.getLogger(__name__)


class Plan(StrEnum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Ordered tiers: higher index = more features.
_PLAN_RANK: dict[str, int] = {
    "starter": 0,
    "professional": 1,
    "enterprise": 2,
}

# Maps feature keys to the minimum plan required.
FEATURE_PLAN_MATRIX: dict[str, Plan] = {
    "datev_export": Plan.PROFESSIONAL,
    "xrechnung": Plan.ENTERPRISE,
    "rag_gap_analysis": Plan.PROFESSIONAL,
    "sso": Plan.ENTERPRISE,
    "scim": Plan.ENTERPRISE,
    "board_pdf_report": Plan.PROFESSIONAL,
    "pdf_reports": Plan.PROFESSIONAL,
    "n8n_webhooks": Plan.ENTERPRISE,
    "custom_branding": Plan.ENTERPRISE,
    "ai_systems": Plan.PROFESSIONAL,
    "risk_register": Plan.PROFESSIONAL,
    "gap_analysis": Plan.PROFESSIONAL,
}


def _get_effective_plan(session: Session, tenant_id: str) -> str | None:
    """Return the effective plan name for a tenant, respecting trial status.

    - Active trial (``trialing`` + not expired) → plan from subscription
      (treated as enterprise-level access).
    - Active subscription (``active``) → plan from subscription.
    - Expired trial or no subscription → ``None``.
    """
    row = (
        session.query(SubscriptionDB)
        .filter(SubscriptionDB.tenant_id == tenant_id)
        .order_by(SubscriptionDB.created_at_utc.desc())
        .first()
    )
    if row is None:
        return None

    now = datetime.now(UTC)

    if row.status == "trialing":
        if row.trial_ends_at is not None:
            trial_end = row.trial_ends_at
            if trial_end.tzinfo is None:
                trial_end = trial_end.replace(tzinfo=UTC)
            if now > trial_end:
                return None  # expired trial
        # Active trial → full enterprise access
        return "enterprise"

    if row.status == "active":
        return row.plan_id

    # paused / canceled / past_due etc.
    return None


def _plan_rank(plan_name: str) -> int:
    return _PLAN_RANK.get(plan_name, -1)


def _check_plan_access(session: Session, tenant_id: str, minimum_plan: Plan) -> None:
    """Raise HTTP 402 if the tenant does not meet the minimum plan requirement."""
    effective = _get_effective_plan(session, tenant_id)
    if effective is None:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "upgrade_required",
                "message_en": ("No active subscription. Please subscribe to access this feature."),
                "message_de": (
                    "Kein aktives Abonnement. Bitte abonnieren Sie, "
                    "um auf diese Funktion zuzugreifen."
                ),
                "required_plan": minimum_plan.value,
                "current_plan": None,
            },
        )

    if _plan_rank(effective) < _plan_rank(minimum_plan.value):
        plan_info = PLAN_CATALOG.get(minimum_plan.value, {})
        display = plan_info.get("display_name", minimum_plan.value.title())
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "upgrade_required",
                "message_en": (
                    f"This feature requires the {display} plan or higher. "
                    "Please upgrade your subscription."
                ),
                "message_de": (
                    f"Diese Funktion erfordert mindestens den {display}-Plan. "
                    "Bitte führen Sie ein Upgrade durch."
                ),
                "required_plan": minimum_plan.value,
                "current_plan": effective,
            },
        )


def require_plan(minimum_plan: Plan):
    """FastAPI dependency that enforces a minimum subscription plan.

    Usage::

        @app.get("/api/v1/enterprise/some-feature")
        def some_feature(
            tenant_id: Annotated[str, Depends(get_api_key_and_tenant)],
            _gate: Annotated[None, Depends(require_plan(Plan.PROFESSIONAL))],
        ):
            ...
    """

    def _dependency(
        tenant_id: str = Depends(get_api_key_and_tenant),
        session: Session = Depends(get_session),
    ) -> None:
        _check_plan_access(session, tenant_id, minimum_plan)

    return _dependency


def check_feature_gate(session: Session, tenant_id: str, feature: str) -> None:
    """Check if a feature is gated and raise 402 if the tenant lacks access.

    Looks up the feature in ``FEATURE_PLAN_MATRIX``. If the feature is not
    listed, access is allowed (un-gated feature).
    """
    required = FEATURE_PLAN_MATRIX.get(feature)
    if required is None:
        return  # feature is not gated
    _check_plan_access(session, tenant_id, required)
