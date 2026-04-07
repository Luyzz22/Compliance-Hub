"""Central SBS domain auto-admin logic.

Verified users with @sbsdeutschland.de or @sbsdeutschland.com email
domains are automatically assigned TENANT_ADMIN role.
The email ki@sbsdeutschland.de is bootstrapped as SUPER_ADMIN.

Only verified emails may receive auto-admin privileges.
"""

from __future__ import annotations

import logging

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


def resolve_auto_role(email: str, *, email_verified: bool) -> EnterpriseRole | None:
    """Determine the automatic role for *email*, or None if no auto-assignment applies.

    - Only verified SBS-domain emails receive auto-admin privileges.
    - ``ki@sbsdeutschland.de`` receives SUPER_ADMIN.
    - Other verified SBS-domain emails receive TENANT_ADMIN.
    - Non-SBS or unverified emails return None (no auto-assignment).
    """
    if not email_verified:
        return None
    normalised = email.strip().lower()
    if not is_sbs_domain(normalised):
        return None
    if normalised == SBS_BOOTSTRAP_EMAIL:
        return EnterpriseRole.SUPER_ADMIN
    return EnterpriseRole.TENANT_ADMIN
