"""Phase 5 tests: Tenant Onboarding Wizard & Subscription Billing.

Covers:
- RBAC: permission checks for billing and onboarding
- Onboarding: status CRUD, step update, completion, templates
- Billing: plan listing, trial subscription, Stripe webhook security
- Feature access check
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.rbac.permissions import Permission, has_permission
from app.rbac.roles import EnterpriseRole
from tests.conftest import _headers

client = TestClient(app)

_TENANT = "board-kpi-tenant"


def _admin_headers() -> dict[str, str]:
    return {**_headers(), "x-opa-user-role": "tenant_admin"}


def _viewer_headers() -> dict[str, str]:
    return {**_headers(), "x-opa-user-role": "viewer"}


# ── RBAC Permission Tests ───────────────────────────────────────────────────


class TestPhase5Permissions:
    def test_tenant_admin_can_manage_billing(self):
        assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.MANAGE_BILLING)

    def test_super_admin_can_manage_billing(self):
        assert has_permission(EnterpriseRole.SUPER_ADMIN, Permission.MANAGE_BILLING)

    def test_viewer_cannot_manage_billing(self):
        assert not has_permission(EnterpriseRole.VIEWER, Permission.MANAGE_BILLING)

    def test_tenant_admin_can_manage_tenant_settings(self):
        assert has_permission(EnterpriseRole.TENANT_ADMIN, Permission.MANAGE_TENANT_SETTINGS)

    def test_viewer_cannot_manage_tenant_settings(self):
        assert not has_permission(EnterpriseRole.VIEWER, Permission.MANAGE_TENANT_SETTINGS)


# ── Onboarding Wizard Tests ─────────────────────────────────────────────────


class TestOnboardingStatus:
    def test_get_status_not_started(self):
        resp = client.get(
            "/api/v1/enterprise/onboarding/status",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_started"

    def test_update_step_creates_record(self):
        resp = client.put(
            "/api/v1/enterprise/onboarding/step/1",
            headers=_admin_headers(),
            json={"industry": "financial_services"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_step"] == 1
        assert data["tenant_id"] == _TENANT
        assert data["completed"] is False

    def test_update_step_advances(self):
        resp = client.put(
            "/api/v1/enterprise/onboarding/step/3",
            headers=_admin_headers(),
            json={"norms_selected": ["DSGVO", "GoBD"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_step"] == 3

    def test_get_status_after_update(self):
        resp = client.get(
            "/api/v1/enterprise/onboarding/status",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "current_step" in data
        assert data["completed"] is False

    def test_complete_onboarding(self):
        resp = client.post(
            "/api/v1/enterprise/onboarding/complete",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["completed"] is True

    def test_invalid_step_rejected(self):
        resp = client.put(
            "/api/v1/enterprise/onboarding/step/0",
            headers=_admin_headers(),
            json={},
        )
        assert resp.status_code == 400

    def test_step_7_rejected(self):
        resp = client.put(
            "/api/v1/enterprise/onboarding/step/7",
            headers=_admin_headers(),
            json={},
        )
        assert resp.status_code == 400


class TestOnboardingTemplates:
    def test_get_templates(self):
        resp = client.get(
            "/api/v1/enterprise/onboarding/templates",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        templates = data["templates"]
        assert "automotive_manufacturing" in templates
        assert "financial_services" in templates
        assert "general" in templates
        assert "DSGVO" in templates["general"]["norms"]

    def test_viewer_can_get_templates(self):
        resp = client.get(
            "/api/v1/enterprise/onboarding/templates",
            headers=_viewer_headers(),
        )
        assert resp.status_code == 200


# ── Billing Plan Tests ───────────────────────────────────────────────────────


class TestBillingPlans:
    def test_list_plans(self):
        resp = client.get(
            "/api/v1/enterprise/billing/plans",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        plans = resp.json()["plans"]
        assert len(plans) == 3
        names = {p["name"] for p in plans}
        assert names == {"starter", "professional", "enterprise"}

    def test_viewer_can_list_plans(self):
        resp = client.get(
            "/api/v1/enterprise/billing/plans",
            headers=_viewer_headers(),
        )
        assert resp.status_code == 200


class TestTrialSubscription:
    def test_create_trial(self):
        resp = client.post(
            "/api/v1/enterprise/billing/subscribe?plan_name=starter",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        sub = resp.json()["subscription"]
        assert sub["status"] == "trialing"
        assert sub["plan_id"] == "starter"
        assert sub["tenant_id"] == _TENANT
        assert sub["trial_ends_at"] is not None

    def test_get_subscription(self):
        resp = client.get(
            "/api/v1/enterprise/billing/subscription",
            headers=_admin_headers(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["subscription"] is not None
        assert data["subscription"]["status"] == "trialing"

    def test_invalid_plan_rejected(self):
        resp = client.post(
            "/api/v1/enterprise/billing/subscribe?plan_name=nonexistent",
            headers=_admin_headers(),
        )
        assert resp.status_code == 400


# ── Stripe Webhook Tests ─────────────────────────────────────────────────────


class TestStripeWebhook:
    def test_webhook_without_secret_returns_501(self):
        with patch.dict(os.environ, {"COMPLIANCEHUB_STRIPE_WEBHOOK_SECRET": ""}):
            resp = client.post(
                "/api/v1/enterprise/billing/stripe-webhook",
                content=b'{"type": "test"}',
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 501

    def test_webhook_without_signature_returns_401(self):
        with patch.dict(os.environ, {"COMPLIANCEHUB_STRIPE_WEBHOOK_SECRET": "whsec_test123"}):
            resp = client.post(
                "/api/v1/enterprise/billing/stripe-webhook",
                content=b'{"type": "test"}',
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401
            assert "Missing Stripe signature" in resp.json()["detail"]

    def test_webhook_invalid_signature_returns_401(self):
        with patch.dict(os.environ, {"COMPLIANCEHUB_STRIPE_WEBHOOK_SECRET": "whsec_test123"}):
            resp = client.post(
                "/api/v1/enterprise/billing/stripe-webhook",
                content=b'{"type": "test"}',
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": "invalid_sig",
                },
            )
            assert resp.status_code == 401
            assert "Invalid Stripe signature" in resp.json()["detail"]

    def test_webhook_valid_signature_accepted(self):
        secret = "whsec_valid_secret"
        payload = json.dumps(
            {
                "type": "customer.subscription.updated",
                "data": {"tenant_id": _TENANT},
            }
        ).encode("utf-8")
        sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        with patch.dict(os.environ, {"COMPLIANCEHUB_STRIPE_WEBHOOK_SECRET": secret}):
            resp = client.post(
                "/api/v1/enterprise/billing/stripe-webhook",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "Stripe-Signature": sig,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "processed"
            assert data["event_type"] == "customer.subscription.updated"


# ── Feature Access Tests ─────────────────────────────────────────────────────


class TestFeatureAccess:
    def test_check_feature_access_with_subscription(self):
        from app.db import get_session
        from app.services.stripe_billing_service import check_feature_access

        session = next(get_session())
        try:
            assert check_feature_access(session, _TENANT, "dashboard") is True
            assert check_feature_access(session, _TENANT, "xrechnung") is False
        finally:
            session.close()

    def test_check_feature_access_no_subscription(self):
        from app.db import get_session
        from app.services.stripe_billing_service import check_feature_access

        session = next(get_session())
        try:
            assert check_feature_access(session, "nonexistent-tenant", "dashboard") is False
        finally:
            session.close()


# ── RBAC Endpoint Tests ──────────────────────────────────────────────────────


class TestBillingRbac:
    def test_viewer_blocked_from_subscription(self):
        resp = client.get(
            "/api/v1/enterprise/billing/subscription",
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403

    def test_viewer_blocked_from_subscribe(self):
        resp = client.post(
            "/api/v1/enterprise/billing/subscribe?plan_name=starter",
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403

    def test_viewer_blocked_from_onboarding_status(self):
        resp = client.get(
            "/api/v1/enterprise/onboarding/status",
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403

    def test_viewer_blocked_from_onboarding_step(self):
        resp = client.put(
            "/api/v1/enterprise/onboarding/step/1",
            headers=_viewer_headers(),
            json={},
        )
        assert resp.status_code == 403

    def test_viewer_blocked_from_onboarding_complete(self):
        resp = client.post(
            "/api/v1/enterprise/onboarding/complete",
            headers=_viewer_headers(),
        )
        assert resp.status_code == 403
