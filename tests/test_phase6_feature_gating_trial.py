"""Phase 6 tests: Feature-Gating Enforcement, Trial Flow, Customer Portal, Webhook Extensions.

Covers:
- Feature-gating middleware (require_plan dependency, HTTP 402)
- Feature matrix enforcement (Starter → Professional feature → 402)
- Trial: full Enterprise access for 14 days → 200
- Expired trial → 402
- Stripe webhook extensions (trial_will_end, payment_succeeded, paused)
- Customer portal session creation
- Trial status / banner endpoint
- Feature check endpoint
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import app
from app.models_db import SubscriptionDB
from app.services.feature_gating import (
    FEATURE_PLAN_MATRIX,
    _get_effective_plan,
    check_feature_gate,
)
from app.services.stripe_billing_service import (
    create_customer_portal_session,
    get_trial_status,
)
from tests.conftest import _headers

client = TestClient(app)

_TENANT = "phase6-test-tenant"
_GATE_TENANT = "phase6-gate-tenant"


def _admin_headers(tenant: str = _TENANT) -> dict[str, str]:
    return {**_headers(), "x-tenant-id": tenant, "x-opa-user-role": "tenant_admin"}


def _viewer_headers(tenant: str = _TENANT) -> dict[str, str]:
    return {**_headers(), "x-tenant-id": tenant, "x-opa-user-role": "viewer"}


def _create_subscription(
    session: Session,
    tenant_id: str,
    plan_id: str = "starter",
    status: str = "active",
    trial_ends_at: datetime | None = None,
) -> SubscriptionDB:
    """Helper: insert a subscription row for testing."""
    now = datetime.now(UTC)
    row = SubscriptionDB(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        plan_id=plan_id,
        status=status,
        trial_ends_at=trial_ends_at,
        current_period_end=now + timedelta(days=30),
        created_at_utc=now,
        updated_at_utc=now,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


# ── Feature-Gating Unit Tests ────────────────────────────────────────────────


class TestFeatureGatingMatrix:
    """Verify the feature-gating matrix logic."""

    def test_starter_blocked_from_professional_feature(self):
        session = next(get_session())
        try:
            _create_subscription(session, "fg-starter-1", plan_id="starter", status="active")
            with pytest.raises(Exception) as exc_info:
                check_feature_gate(session, "fg-starter-1", "datev_export")
            assert exc_info.value.status_code == 402
            detail = exc_info.value.detail
            assert detail["error"] == "upgrade_required"
            assert detail["required_plan"] == "professional"
            assert detail["current_plan"] == "starter"
        finally:
            session.close()

    def test_starter_blocked_from_enterprise_feature(self):
        session = next(get_session())
        try:
            _create_subscription(session, "fg-starter-2", plan_id="starter", status="active")
            with pytest.raises(Exception) as exc_info:
                check_feature_gate(session, "fg-starter-2", "xrechnung")
            assert exc_info.value.status_code == 402
            assert exc_info.value.detail["required_plan"] == "enterprise"
        finally:
            session.close()

    def test_professional_can_access_professional_feature(self):
        session = next(get_session())
        try:
            _create_subscription(session, "fg-pro-1", plan_id="professional", status="active")
            # Should not raise
            check_feature_gate(session, "fg-pro-1", "datev_export")
        finally:
            session.close()

    def test_professional_blocked_from_enterprise_feature(self):
        session = next(get_session())
        try:
            _create_subscription(session, "fg-pro-2", plan_id="professional", status="active")
            with pytest.raises(Exception) as exc_info:
                check_feature_gate(session, "fg-pro-2", "sso")
            assert exc_info.value.status_code == 402
            assert exc_info.value.detail["required_plan"] == "enterprise"
        finally:
            session.close()

    def test_enterprise_can_access_all_features(self):
        session = next(get_session())
        try:
            _create_subscription(session, "fg-ent-1", plan_id="enterprise", status="active")
            for feature in FEATURE_PLAN_MATRIX:
                check_feature_gate(session, "fg-ent-1", feature)
        finally:
            session.close()

    def test_ungated_feature_always_allowed(self):
        session = next(get_session())
        try:
            _create_subscription(session, "fg-ungated", plan_id="starter", status="active")
            check_feature_gate(session, "fg-ungated", "dashboard")
        finally:
            session.close()

    def test_no_subscription_returns_402(self):
        session = next(get_session())
        try:
            with pytest.raises(Exception) as exc_info:
                check_feature_gate(session, "no-sub-tenant", "datev_export")
            assert exc_info.value.status_code == 402
            assert exc_info.value.detail["current_plan"] is None
        finally:
            session.close()


# ── Trial Access Tests ───────────────────────────────────────────────────────


class TestTrialAccess:
    """Trial subscriptions get full Enterprise access for 14 days."""

    def test_active_trial_gets_enterprise_access(self):
        session = next(get_session())
        try:
            _create_subscription(
                session,
                "fg-trial-1",
                plan_id="enterprise",
                status="trialing",
                trial_ends_at=datetime.now(UTC) + timedelta(days=10),
            )
            # Should have enterprise access
            effective = _get_effective_plan(session, "fg-trial-1")
            assert effective == "enterprise"
            # Should be able to access enterprise features
            check_feature_gate(session, "fg-trial-1", "xrechnung")
            check_feature_gate(session, "fg-trial-1", "sso")
        finally:
            session.close()

    def test_expired_trial_returns_402(self):
        session = next(get_session())
        try:
            _create_subscription(
                session,
                "fg-trial-expired",
                plan_id="enterprise",
                status="trialing",
                trial_ends_at=datetime.now(UTC) - timedelta(days=1),
            )
            effective = _get_effective_plan(session, "fg-trial-expired")
            assert effective is None
            with pytest.raises(Exception) as exc_info:
                check_feature_gate(session, "fg-trial-expired", "datev_export")
            assert exc_info.value.status_code == 402
        finally:
            session.close()

    def test_trial_starter_still_gets_enterprise(self):
        """Even a starter-plan trial gets enterprise access during trial period."""
        session = next(get_session())
        try:
            _create_subscription(
                session,
                "fg-trial-starter",
                plan_id="starter",
                status="trialing",
                trial_ends_at=datetime.now(UTC) + timedelta(days=14),
            )
            effective = _get_effective_plan(session, "fg-trial-starter")
            assert effective == "enterprise"
        finally:
            session.close()


# ── Stripe Webhook Extension Tests ───────────────────────────────────────────


class TestStripeWebhookExtensions:
    """Test new webhook event types: trial_will_end, payment_succeeded, paused."""

    def _post_webhook(self, event_type: str, event_data: dict) -> dict:
        secret = "whsec_phase6_test"
        payload = json.dumps({"type": event_type, "data": event_data}).encode("utf-8")
        sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        with patch.dict(os.environ, {"COMPLIANCEHUB_STRIPE_WEBHOOK_SECRET": secret}):
            resp = client.post(
                "/api/v1/enterprise/billing/stripe-webhook",
                content=payload,
                headers={"Content-Type": "application/json", "Stripe-Signature": sig},
            )
        return resp

    def test_trial_will_end_processed(self):
        resp = self._post_webhook(
            "customer.subscription.trial_will_end",
            {"tenant_id": _TENANT},
        )
        assert resp.status_code == 200
        assert resp.json()["event_type"] == "customer.subscription.trial_will_end"
        assert resp.json()["status"] == "processed"

    def test_payment_succeeded_processed(self):
        resp = self._post_webhook(
            "invoice.payment_succeeded",
            {"tenant_id": _TENANT, "stripe_event_id": "evt_pay_123"},
        )
        assert resp.status_code == 200
        assert resp.json()["event_type"] == "invoice.payment_succeeded"

    def test_subscription_paused_processed(self):
        resp = self._post_webhook(
            "customer.subscription.paused",
            {"tenant_id": _TENANT, "stripe_subscription_id": "sub_pause_test"},
        )
        assert resp.status_code == 200
        assert resp.json()["event_type"] == "customer.subscription.paused"


# ── Customer Portal Tests ────────────────────────────────────────────────────


class TestCustomerPortal:
    def test_create_portal_session(self):
        result = create_customer_portal_session(
            tenant_id="portal-tenant",
            stripe_customer_id="cus_test123",
            return_url="https://app.compliancehub.de/billing",
        )
        assert result["tenant_id"] == "portal-tenant"
        assert result["stripe_customer_id"] == "cus_test123"
        assert "portal_url" in result
        assert result["return_url"] == "https://app.compliancehub.de/billing"

    def test_portal_endpoint_no_customer_returns_400(self):
        resp = client.post(
            "/api/v1/enterprise/billing/portal-session",
            headers=_admin_headers("portal-no-customer"),
        )
        assert resp.status_code == 400


# ── Trial Status / Banner Tests ──────────────────────────────────────────────


class TestTrialStatus:
    def test_trial_status_active(self):
        session = next(get_session())
        try:
            _create_subscription(
                session,
                "trial-banner-1",
                plan_id="enterprise",
                status="trialing",
                trial_ends_at=datetime.now(UTC) + timedelta(days=7),
            )
            result = get_trial_status(session, "trial-banner-1")
            assert result["is_trialing"] is True
            assert result["days_remaining"] > 0
            assert result["trial_ends_at"] is not None
            assert result["plan_id"] == "enterprise"
        finally:
            session.close()

    def test_trial_status_expired(self):
        session = next(get_session())
        try:
            _create_subscription(
                session,
                "trial-banner-exp",
                plan_id="enterprise",
                status="trialing",
                trial_ends_at=datetime.utcnow() - timedelta(days=1),
            )
            result = get_trial_status(session, "trial-banner-exp")
            assert result["is_trialing"] is False
            assert result["days_remaining"] == 0
        finally:
            session.close()

    def test_trial_status_no_subscription(self):
        session = next(get_session())
        try:
            result = get_trial_status(session, "no-sub-banner-tenant")
            assert result["is_trialing"] is False
            assert result["days_remaining"] == 0
            assert result["plan_id"] is None
        finally:
            session.close()

    def test_trial_banner_endpoint(self):
        # First create a subscription via API
        resp = client.post(
            "/api/v1/enterprise/billing/subscribe?plan_name=enterprise",
            headers=_admin_headers("trial-banner-api"),
        )
        assert resp.status_code == 200

        resp = client.get(
            "/api/v1/enterprise/billing/trial-status",
            headers=_viewer_headers("trial-banner-api"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_trialing"] is True
        assert data["days_remaining"] > 0


# ── Feature Check Endpoint Tests ─────────────────────────────────────────────


class TestFeatureCheckEndpoint:
    def test_feature_check_accessible(self):
        # Create active enterprise subscription
        resp = client.post(
            "/api/v1/enterprise/billing/subscribe?plan_name=enterprise",
            headers=_admin_headers("fc-ent"),
        )
        assert resp.status_code == 200

        resp = client.get(
            "/api/v1/enterprise/billing/feature-check?feature=xrechnung",
            headers=_viewer_headers("fc-ent"),
        )
        # Trial = enterprise access
        assert resp.status_code == 200
        assert resp.json()["accessible"] is True

    def test_feature_check_blocked(self):
        # Create active starter subscription
        session = next(get_session())
        try:
            _create_subscription(session, "fc-starter", plan_id="starter", status="active")
        finally:
            session.close()

        resp = client.get(
            "/api/v1/enterprise/billing/feature-check?feature=datev_export",
            headers=_viewer_headers("fc-starter"),
        )
        assert resp.status_code == 402
        detail = resp.json()["detail"]
        assert detail["error"] == "upgrade_required"
        assert detail["required_plan"] == "professional"

    def test_feature_check_ungated(self):
        resp = client.get(
            "/api/v1/enterprise/billing/feature-check?feature=dashboard",
            headers=_viewer_headers("fc-starter"),
        )
        assert resp.status_code == 200
        assert resp.json()["accessible"] is True
