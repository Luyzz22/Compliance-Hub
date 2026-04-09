"""n8n webhook integration service — trigger workflows and verify payloads.

Provides HMAC-SHA256 signing, payload construction, and HTTP dispatch
for n8n automation workflows (board reports, DATEV exports, reminders).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from datetime import UTC, datetime
from enum import StrEnum

import httpx

logger = logging.getLogger(__name__)


class N8nWorkflowType(StrEnum):
    """Supported n8n automation workflow types."""

    monthly_board_report = "monthly_board_report"
    datev_monthly_export = "datev_monthly_export"
    deadline_reminder = "deadline_reminder"
    gap_analysis_trigger = "gap_analysis_trigger"
    access_review_reminder = "access_review_reminder"


def compute_hmac_signature(payload: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 hex digest for *payload* using *secret*."""
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_hmac_signature(payload: bytes, secret: str, signature: str) -> bool:
    """Verify that *signature* matches the expected HMAC-SHA256 of *payload*."""
    expected = compute_hmac_signature(payload, secret)
    return hmac.compare_digest(expected, signature)


def build_webhook_payload(event_type: str, tenant_id: str, data: dict) -> dict:
    """Build a standardised webhook payload for n8n consumption.

    Returns a dict with keys: event_type, tenant_id, timestamp, correlation_id, data.
    """
    return {
        "event_type": event_type,
        "tenant_id": tenant_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "correlation_id": str(uuid.uuid4()),
        "data": data,
    }


def trigger_n8n_webhook(
    webhook_url: str,
    payload: dict,
    secret: str | None = None,
) -> dict:
    """Send an HTTP POST to an n8n webhook endpoint.

    If *secret* is provided the request includes an ``X-Hub-Signature-256``
    header with the HMAC-SHA256 of the JSON body.

    Returns a dict with ``status_code`` and ``body`` on success, or
    ``error`` on failure.
    """
    import json

    body_bytes = json.dumps(payload, default=str).encode("utf-8")

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if secret:
        sig = compute_hmac_signature(body_bytes, secret)
        headers["X-Hub-Signature-256"] = f"sha256={sig}"

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(webhook_url, content=body_bytes, headers=headers)
        logger.info(
            "n8n_webhook_sent url=%s status=%d event=%s",
            webhook_url,
            response.status_code,
            payload.get("event_type", "unknown"),
        )
        return {"status_code": response.status_code, "body": response.text}
    except httpx.HTTPError as exc:
        logger.exception("n8n_webhook_failed url=%s error=%s", webhook_url, exc)
        return {"error": str(exc)}
