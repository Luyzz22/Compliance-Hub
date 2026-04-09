"""Stripe billing service – subscription management and webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models_db import BillingEventDB, SubscriptionDB

logger = logging.getLogger(__name__)

PLAN_CATALOG: dict[str, dict] = {
    "starter": {
        "name": "starter",
        "display_name": "Starter",
        "max_users": 5,
        "features": ["dashboard", "compliance_calendar", "basic_reports"],
        "price_monthly_cents": 4900,
    },
    "professional": {
        "name": "professional",
        "display_name": "Professional",
        "max_users": 25,
        "features": [
            "dashboard",
            "compliance_calendar",
            "basic_reports",
            "ai_systems",
            "risk_register",
            "gap_analysis",
            "pdf_reports",
        ],
        "price_monthly_cents": 14900,
    },
    "enterprise": {
        "name": "enterprise",
        "display_name": "Enterprise",
        "max_users": None,
        "features": [
            "dashboard",
            "compliance_calendar",
            "basic_reports",
            "ai_systems",
            "risk_register",
            "gap_analysis",
            "pdf_reports",
            "xrechnung",
            "n8n_webhooks",
            "sso",
            "scim",
            "custom_branding",
        ],
        "price_monthly_cents": 49900,
    },
}


def get_plans() -> list[dict]:
    """Return all available subscription plans."""
    return list(PLAN_CATALOG.values())


def _sub_to_dict(row: SubscriptionDB) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "plan_id": row.plan_id,
        "stripe_subscription_id": row.stripe_subscription_id,
        "stripe_customer_id": row.stripe_customer_id,
        "status": row.status,
        "trial_ends_at": row.trial_ends_at.isoformat() if row.trial_ends_at else None,
        "current_period_end": (
            row.current_period_end.isoformat() if row.current_period_end else None
        ),
        "created_at_utc": row.created_at_utc.isoformat() if row.created_at_utc else None,
        "updated_at_utc": row.updated_at_utc.isoformat() if row.updated_at_utc else None,
    }


def get_tenant_subscription(session: Session, tenant_id: str) -> dict | None:
    """Return the active subscription for a tenant, or None."""
    row = (
        session.query(SubscriptionDB)
        .filter(SubscriptionDB.tenant_id == tenant_id)
        .order_by(SubscriptionDB.created_at_utc.desc())
        .first()
    )
    if row is None:
        return None
    return _sub_to_dict(row)


def create_trial_subscription(session: Session, tenant_id: str, plan_name: str) -> dict:
    """Create a 14-day trial subscription for a tenant."""
    plan = PLAN_CATALOG.get(plan_name)
    if plan is None:
        raise ValueError(f"Unknown plan: {plan_name}")

    now = datetime.utcnow()
    row = SubscriptionDB(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        plan_id=plan_name,
        status="trialing",
        trial_ends_at=now + timedelta(days=14),
        current_period_end=now + timedelta(days=14),
        created_at_utc=now,
        updated_at_utc=now,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    logger.info("trial_subscription_created tenant=%s plan=%s", tenant_id, plan_name)
    return _sub_to_dict(row)


def handle_stripe_webhook_event(session: Session, event_type: str, event_data: dict) -> dict:
    """Process a Stripe webhook event and log it."""
    tenant_id = event_data.get("tenant_id", "unknown")
    event = BillingEventDB(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        event_type=event_type,
        stripe_event_id=event_data.get("stripe_event_id"),
        payload=event_data,
        created_at_utc=datetime.utcnow(),
    )
    session.add(event)

    # Update subscription status based on event type
    if event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub_id = event_data.get("stripe_subscription_id")
        if sub_id:
            sub = (
                session.query(SubscriptionDB)
                .filter(SubscriptionDB.stripe_subscription_id == sub_id)
                .first()
            )
            if sub:
                new_status = event_data.get("status", sub.status)
                sub.status = new_status
                sub.updated_at_utc = datetime.utcnow()

    elif event_type == "customer.subscription.trial_will_end":
        logger.info("trial_will_end tenant=%s – sending reminder", tenant_id)

    elif event_type == "invoice.payment_succeeded":
        logger.info("payment_succeeded tenant=%s", tenant_id)

    elif event_type == "customer.subscription.paused":
        sub_id = event_data.get("stripe_subscription_id")
        if sub_id:
            sub = (
                session.query(SubscriptionDB)
                .filter(SubscriptionDB.stripe_subscription_id == sub_id)
                .first()
            )
            if sub:
                sub.status = "paused"
                sub.updated_at_utc = datetime.utcnow()

    session.commit()
    logger.info("stripe_webhook_processed tenant=%s event_type=%s", tenant_id, event_type)
    return {"status": "processed", "event_type": event_type, "tenant_id": tenant_id}


def verify_stripe_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Stripe webhook HMAC-SHA256 signature."""
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def check_feature_access(session: Session, tenant_id: str, feature: str) -> bool:
    """Check if a tenant's subscription includes a given feature."""
    sub = get_tenant_subscription(session, tenant_id)
    if sub is None:
        return False
    plan = PLAN_CATALOG.get(sub["plan_id"])
    if plan is None:
        return False
    return feature in plan["features"]


def create_customer_portal_session(
    tenant_id: str,
    stripe_customer_id: str,
    return_url: str,
) -> dict:
    """Create a Stripe Customer Portal session for self-service billing management.

    In production, this calls ``stripe.billing_portal.Session.create()``.
    For now returns a portal URL structure that the frontend can redirect to.
    """
    portal_url = f"https://billing.stripe.com/p/session/{stripe_customer_id}"
    logger.info(
        "customer_portal_session_created tenant=%s customer=%s",
        tenant_id,
        stripe_customer_id,
    )
    return {
        "portal_url": portal_url,
        "tenant_id": tenant_id,
        "stripe_customer_id": stripe_customer_id,
        "return_url": return_url,
    }


def get_trial_status(session: Session, tenant_id: str) -> dict:
    """Return trial status information for the in-app trial banner.

    Returns a dict with:
    - ``is_trialing``: whether the tenant is currently in a trial
    - ``days_remaining``: number of days left (0 if not trialing)
    - ``trial_ends_at``: ISO timestamp of trial end (None if not trialing)
    - ``plan_id``: current plan name
    """
    row = (
        session.query(SubscriptionDB)
        .filter(SubscriptionDB.tenant_id == tenant_id)
        .order_by(SubscriptionDB.created_at_utc.desc())
        .first()
    )
    if row is None:
        return {
            "is_trialing": False,
            "days_remaining": 0,
            "trial_ends_at": None,
            "plan_id": None,
        }

    if row.status != "trialing" or row.trial_ends_at is None:
        return {
            "is_trialing": False,
            "days_remaining": 0,
            "trial_ends_at": None,
            "plan_id": row.plan_id,
        }

    now = datetime.now(UTC)
    trial_end = row.trial_ends_at
    if trial_end.tzinfo is None:
        trial_end = trial_end.replace(tzinfo=UTC)
    remaining = (trial_end - now).days
    if remaining < 0:
        remaining = 0

    return {
        "is_trialing": remaining > 0,
        "days_remaining": remaining,
        "trial_ends_at": row.trial_ends_at.isoformat() if row.trial_ends_at else None,
        "plan_id": row.plan_id,
    }
