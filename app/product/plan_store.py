"""In-memory tenant plan store and capability resolution.

Fast, cache-friendly lookups for capability checks at API and UI level.
Tenants without an explicit plan config get a default starter tier.
"""

from __future__ import annotations

import logging
from threading import Lock

from app.product.models import (
    CAPABILITY_LABELS,
    Capability,
    ProductTier,
    TenantPlanConfig,
)
from app.services.rag.evidence_store import record_event

logger = logging.getLogger(__name__)

_lock = Lock()
_plans: dict[str, TenantPlanConfig] = {}

_DEFAULT_PLAN = TenantPlanConfig(tenant_id="__default__", tier=ProductTier.starter)


def set_tenant_plan(plan: TenantPlanConfig) -> TenantPlanConfig:
    """Assign or update a tenant's product plan."""
    with _lock:
        _plans[plan.tenant_id] = plan
    logger.info(
        "tenant_plan_set",
        extra={
            "tenant_id": plan.tenant_id,
            "tier": plan.tier.value,
            "bundles": sorted(plan.bundles),
        },
    )
    return plan


def get_tenant_plan(tenant_id: str) -> TenantPlanConfig:
    """Return the plan for a tenant, defaulting to starter if unset."""
    with _lock:
        plan = _plans.get(tenant_id)
    if plan is not None:
        return plan
    return TenantPlanConfig(tenant_id=tenant_id, tier=ProductTier.starter)


def has_capability(tenant_id: str, cap: Capability) -> bool:
    """Check if a tenant has a specific capability. Fast path."""
    return get_tenant_plan(tenant_id).has_capability(cap)


def list_tenant_plans() -> list[TenantPlanConfig]:
    """List all explicitly configured tenant plans (internal/admin)."""
    with _lock:
        return list(_plans.values())


def clear_for_tests() -> None:
    with _lock:
        _plans.clear()


# ---------------------------------------------------------------------------
# Capability enforcement helper (raises HTTPException)
# ---------------------------------------------------------------------------

from fastapi import HTTPException, status  # noqa: E402


def require_capability(tenant_id: str, cap: Capability) -> None:
    """Raise 403 if the tenant lacks the required capability."""
    if has_capability(tenant_id, cap):
        return

    from app.product.copy_de import (
        CAPABILITY_UPGRADE_HINTS_DE,
        CONTACT_URL,
        FEATURE_NOT_ENABLED_DISCLAIMER_DE,
    )

    plan = get_tenant_plan(tenant_id)
    labels = CAPABILITY_LABELS.get(cap, {})
    label_de = labels.get("de", cap.value)
    label_en = labels.get("en", cap.value)
    plan_label = plan.plan_display()
    upgrade_hint = CAPABILITY_UPGRADE_HINTS_DE.get(cap, "")

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "error": "feature_not_enabled",
            "message_en": (
                f"This feature ({label_en}) is not included in your current plan. "
                f"Contact your ComplianceHub representative to upgrade."
            ),
            "message_de": (
                f"Diese Funktion ({label_de}) ist in Ihrem aktuellen Paket "
                f"({plan_label}) nicht enthalten."
            ),
            "upgrade_hint_de": (
                f"Diese Funktion ist typischerweise im Paket '{upgrade_hint}' verfügbar."
                if upgrade_hint
                else ""
            ),
            "contact_cta_de": (
                "Für ein Upgrade oder weitere Informationen: kontakt@compliancehub.de"
            ),
            "contact_url": CONTACT_URL,
            "disclaimer_de": FEATURE_NOT_ENABLED_DISCLAIMER_DE,
            "capability": cap.value,
            "current_plan": plan_label,
        },
    )


# ---------------------------------------------------------------------------
# Usage metrics
# ---------------------------------------------------------------------------


def log_capability_usage(
    *,
    tenant_id: str,
    capability: str,
    action: str,
    bundle: str = "",
) -> None:
    """Record a feature usage event for packaging analytics."""
    plan = get_tenant_plan(tenant_id)
    record_event(
        {
            "event_type": "capability_usage",
            "tenant_id": tenant_id,
            "capability": capability,
            "action": action,
            "tier": plan.tier.value,
            "bundle": bundle or _primary_bundle_for_cap(plan, capability),
        }
    )


def _primary_bundle_for_cap(plan: TenantPlanConfig, cap_value: str) -> str:
    """Best-effort: find the first bundle that grants this capability."""
    try:
        cap = Capability(cap_value)
    except ValueError:
        return ""
    for bundle in plan.effective_bundles():
        from app.product.models import BUNDLE_CAPABILITIES

        if cap in BUNDLE_CAPABILITIES.get(bundle, frozenset()):
            return bundle.value
    return ""
