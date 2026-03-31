"""Pre-configured demo tenant plans for sales/demo environments.

Each plan profile represents a typical DACH customer segment:
- Kanzlei Demo: Pro tier with governance + evidence bundles
- SAP Demo: Enterprise with full integrations
- SME Demo: Starter with AI Act Readiness only
"""

from __future__ import annotations

from app.product.models import ProductBundle, ProductTier, TenantPlanConfig
from app.product.plan_store import set_tenant_plan

DEMO_PLAN_PROFILES: dict[str, TenantPlanConfig] = {
    "kanzlei_demo": TenantPlanConfig(
        tenant_id="",
        tier=ProductTier.pro,
        bundles={
            ProductBundle.ai_act_readiness,
            ProductBundle.ai_governance_evidence,
        },
        label="Kanzlei Demo (Pro)",
    ),
    "sap_demo": TenantPlanConfig(
        tenant_id="",
        tier=ProductTier.enterprise,
        bundles={
            ProductBundle.ai_act_readiness,
            ProductBundle.ai_governance_evidence,
            ProductBundle.enterprise_integrations,
        },
        label="SAP Enterprise Demo",
    ),
    "sme_demo": TenantPlanConfig(
        tenant_id="",
        tier=ProductTier.starter,
        bundles={ProductBundle.ai_act_readiness},
        label="SME Demo (Starter)",
    ),
}


def seed_demo_plan(tenant_id: str, profile: str) -> TenantPlanConfig | None:
    """Apply a demo plan profile to a tenant. Returns None if profile unknown."""
    template = DEMO_PLAN_PROFILES.get(profile)
    if template is None:
        return None
    plan = template.model_copy(update={"tenant_id": tenant_id})
    return set_tenant_plan(plan)


def list_profiles() -> list[str]:
    return sorted(DEMO_PLAN_PROFILES.keys())
