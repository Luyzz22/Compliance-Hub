"""Production egress URL, signature and forbidden-provider boundaries."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.outbound_policy import (
    OutboundPolicyError,
    approved_outbound_url,
    approved_private_service_base_url,
    configured_outbound_url,
)
from app.services.board_report_export_jobs import _signed_payload
from app.services.n8n_webhook_service import trigger_n8n_webhook
from app.services.stripe_billing_service import (
    ExternalBillingProviderForbidden,
    create_customer_portal_session,
)


def test_production_outbound_url_requires_https_and_exact_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("COMPLIANCEHUB_N8N_ALLOWED_HOSTS", "n8n.internal.example")

    assert (
        approved_outbound_url(
            "https://n8n.internal.example/hooks/compliancehub",
            allowlist_variable="COMPLIANCEHUB_N8N_ALLOWED_HOSTS",
        )
        == "https://n8n.internal.example/hooks/compliancehub"
    )
    with pytest.raises(OutboundPolicyError, match="HTTPS"):
        approved_outbound_url(
            "http://n8n.internal.example/hooks/compliancehub",
            allowlist_variable="COMPLIANCEHUB_N8N_ALLOWED_HOSTS",
        )
    with pytest.raises(OutboundPolicyError, match="must be listed"):
        approved_outbound_url(
            "https://other.internal.example/hooks/compliancehub",
            allowlist_variable="COMPLIANCEHUB_N8N_ALLOWED_HOSTS",
        )


def test_forbidden_provider_and_query_secret_cannot_be_allowlisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("COMPLIANCEHUB_N8N_ALLOWED_HOSTS", "billing.stripe.com")

    with pytest.raises(OutboundPolicyError, match="provider forbidden"):
        approved_outbound_url(
            "https://billing.stripe.com/session",
            allowlist_variable="COMPLIANCEHUB_N8N_ALLOWED_HOSTS",
        )


def test_private_opa_service_requires_an_exact_production_host_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("COMPLIANCEHUB_OPA_ALLOWED_HOSTS", "opa")

    assert (
        approved_private_service_base_url(
            "http://opa:8181",
            allowlist_variable="COMPLIANCEHUB_OPA_ALLOWED_HOSTS",
        )
        == "http://opa:8181"
    )
    with pytest.raises(OutboundPolicyError, match="must be listed"):
        approved_private_service_base_url(
            "https://policy.external.example",
            allowlist_variable="COMPLIANCEHUB_OPA_ALLOWED_HOSTS",
        )
    with pytest.raises(OutboundPolicyError, match="query parameters"):
        approved_outbound_url(
            "https://n8n.internal.example/hook?secret=exposed",
            allowlist_variable="COMPLIANCEHUB_N8N_ALLOWED_HOSTS",
        )


def test_production_n8n_dispatch_requires_a_signing_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("COMPLIANCEHUB_N8N_ALLOWED_HOSTS", "n8n.internal.example")
    monkeypatch.setenv(
        "COMPLIANCEHUB_N8N_WEBHOOK_URL",
        "https://n8n.internal.example/hooks/compliancehub",
    )

    with pytest.raises(OutboundPolicyError, match="signing secret"):
        trigger_n8n_webhook(
            {"event_type": "test"},
        )


def test_configured_outbound_url_ignores_request_data_and_uses_deployment_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("COMPLIANCEHUB_N8N_ALLOWED_HOSTS", "n8n.internal.example")
    monkeypatch.setenv(
        "COMPLIANCEHUB_N8N_WEBHOOK_URL",
        "https://n8n.internal.example/hooks/governed",
    )

    assert (
        configured_outbound_url(
            url_variable="COMPLIANCEHUB_N8N_WEBHOOK_URL",
            allowlist_variable="COMPLIANCEHUB_N8N_ALLOWED_HOSTS",
        )
        == "https://n8n.internal.example/hooks/governed"
    )


def test_stripe_portal_and_webhook_are_unavailable_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")

    with pytest.raises(ExternalBillingProviderForbidden):
        create_customer_portal_session("tenant", "customer", "https://app.example")

    response = TestClient(app).post(
        "/api/v1/enterprise/billing/stripe-webhook",
        content=b"{}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 503
    assert (
        response.json()["detail"] == "External billing provider is not approved in this deployment"
    )


def test_production_export_payload_is_signed_from_mounted_secret(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secret = "export-signing-secret-with-at-least-32-bytes"
    secret_path = tmp_path / "export-webhook-secret"
    secret_path.write_text(secret, encoding="utf-8")
    secret_path.chmod(0o400)
    monkeypatch.setenv("COMPLIANCEHUB_ENV", "production")
    monkeypatch.setenv("COMPLIANCEHUB_EXPORT_WEBHOOK_SECRET_FILE", str(secret_path))

    body, headers = _signed_payload({"tenant_id": "tenant-1", "value": 7})

    expected_body = json.dumps(
        {"tenant_id": "tenant-1", "value": 7}, default=str, separators=(",", ":")
    ).encode("utf-8")
    expected_signature = hmac.new(secret.encode("utf-8"), expected_body, hashlib.sha256).hexdigest()
    assert body == expected_body
    assert headers["X-Hub-Signature-256"] == f"sha256={expected_signature}"
