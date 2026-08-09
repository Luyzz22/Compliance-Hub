"""Central SBS domain auto-admin logic.

Verified users with @sbsdeutschland.de or @sbsdeutschland.com email
domains are automatically assigned TENANT_ADMIN role.
The email ki@sbsdeutschland.de is bootstrapped as SUPER_ADMIN.

Only verified emails may receive auto-admin privileges.
"""

from __future__ import annotations

import logging
import os

from app.rbac.roles import EnterpriseRole

logger = logging.getLogger(__name__)

# Domains that qualify for automatic admin role assignment.
SBS_ADMIN_DOMAINS: frozenset[str] = frozenset({"sbsdeutschland.de", "sbsdeutschland.com"})

# Bootstrap email that always receives SUPER_ADMIN.
SBS_BOOTSTRAP_EMAIL: str = "ki@sbsdeutschland.de"


def is_sbs_domain(email: str) -> bool:
    """Return True if *email* belongs to an SBS admin domain (case-insensitive)."""
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1].lower().strip()
    return domain in SBS_ADMIN_DOMAINS


def auto_admin_enabled() -> bool:
    """Return True if domain-based auto-admin may assign privileges.

    Binding a privileged role to an e-mail domain makes administrative access depend on
    control over that domain and on the mail-verification path. That is acceptable for
    operator bootstrapping in development, but it must not be the default in production.
    Production therefore requires an explicit opt-in.
    """
    environment = os.getenv("COMPLIANCEHUB_ENV", "dev").strip().lower()
    if environment not in {"prod", "production"}:
        return True
    raw = os.getenv("COMPLIANCEHUB_ALLOW_DOMAIN_AUTO_ADMIN", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def resolve_auto_role(email: str, *, email_verified: bool) -> EnterpriseRole | None:
    """Determine the automatic role for *email*, or None if no auto-assignment applies.

    - Disabled in production unless ``COMPLIANCEHUB_ALLOW_DOMAIN_AUTO_ADMIN`` is set.
    - Only verified SBS-domain emails receive auto-admin privileges.
    - ``ki@sbsdeutschland.de`` receives SUPER_ADMIN.
    - Other verified SBS-domain emails receive TENANT_ADMIN.
    - Non-SBS or unverified emails return None (no auto-assignment).
    """
    if not email_verified:
        return None
    if not auto_admin_enabled():
        logger.info("domain_auto_admin_suppressed_in_production")
        return None
    normalised = email.strip().lower()
    if not is_sbs_domain(normalised):
        return None
    if normalised == SBS_BOOTSTRAP_EMAIL:
        return EnterpriseRole.SUPER_ADMIN
    return EnterpriseRole.TENANT_ADMIN
