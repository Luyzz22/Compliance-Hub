"""Fail-closed policy for application-controlled outbound HTTP destinations."""

from __future__ import annotations

import os
from urllib.parse import urlsplit


class OutboundPolicyError(ValueError):
    """An outbound destination contradicts the production egress contract."""


_FORBIDDEN_PROVIDER_SUFFIXES = (
    "hubapi.com",
    "hubspot.com",
    "pipedrive.com",
    "stripe.com",
    "vercel.app",
    "vercel.com",
    "neon.tech",
    "posthog.com",
    "sentry.io",
)


def is_production_runtime() -> bool:
    return os.getenv("COMPLIANCEHUB_ENV", "dev").strip().lower() in {
        "prod",
        "production",
    }


def _allowed_hosts(variable_name: str) -> set[str]:
    return {
        value.strip().rstrip(".").lower()
        for value in os.getenv(variable_name, "").split(",")
        if value.strip()
    }


def _matches_suffix(hostname: str, suffix: str) -> bool:
    return hostname == suffix or hostname.endswith(f".{suffix}")


def approved_outbound_url(raw: str, *, allowlist_variable: str) -> str:
    """Validate a webhook/export URL and return the original, stripped value.

    Network-level DNS/IP enforcement remains the responsibility of the Hetzner egress
    proxy.  This application boundary ensures every production target is explicit and
    prevents credentials or query secrets from being embedded in stored URLs.
    """

    value = raw.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise OutboundPolicyError("outbound URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise OutboundPolicyError(
            "outbound URL must not contain credentials, query parameters or fragments"
        )
    if not is_production_runtime():
        return value
    if parsed.scheme != "https":
        raise OutboundPolicyError("outbound URL must use HTTPS in production")

    hostname = parsed.hostname.rstrip(".").lower()
    if any(_matches_suffix(hostname, suffix) for suffix in _FORBIDDEN_PROVIDER_SUFFIXES):
        raise OutboundPolicyError("outbound URL targets a provider forbidden in production")
    if hostname not in _allowed_hosts(allowlist_variable):
        raise OutboundPolicyError(f"outbound URL host must be listed in {allowlist_variable}")
    return value


def approved_private_service_base_url(raw: str, *, allowlist_variable: str) -> str:
    """Validate an internal service base URL such as the Docker-network OPA endpoint."""

    value = raw.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise OutboundPolicyError("private service URL must be an absolute HTTP(S) URL")
    if (
        parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise OutboundPolicyError(
            "private service URL must be a bare origin without credentials or parameters"
        )
    if not is_production_runtime():
        return value.rstrip("/")

    hostname = parsed.hostname.rstrip(".").lower()
    if any(_matches_suffix(hostname, suffix) for suffix in _FORBIDDEN_PROVIDER_SUFFIXES):
        raise OutboundPolicyError("private service URL targets a forbidden provider")
    if hostname not in _allowed_hosts(allowlist_variable):
        raise OutboundPolicyError(f"private service host must be listed in {allowlist_variable}")
    return value.rstrip("/")
