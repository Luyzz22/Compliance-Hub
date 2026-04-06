"""Product packaging domain model.

Defines tiers, bundles, capabilities, and the mapping between them.
These are the building blocks for DACH-market product packages:
- Starter: AI Act Readiness (Einstieg für KMU)
- Pro: AI Governance + Evidence (Wachstumsphase Kanzlei/Mittelstand)
- Enterprise: Full platform + SAP/DATEV connectors
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ProductTier(StrEnum):
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class ProductBundle(StrEnum):
    ai_act_readiness = "ai_act_readiness"
    ai_governance_evidence = "ai_governance_evidence"
    enterprise_integrations = "enterprise_integrations"


class Capability(StrEnum):
    ai_advisor_basic = "cap_ai_advisor_basic"
    ai_evidence_basic = "cap_ai_evidence_basic"
    grc_records = "cap_grc_records"
    ai_system_inventory = "cap_ai_system_inventory"
    kanzlei_reports = "cap_kanzlei_reports"
    enterprise_integrations = "cap_enterprise_integrations"


BUNDLE_CAPABILITIES: dict[ProductBundle, frozenset[Capability]] = {
    ProductBundle.ai_act_readiness: frozenset(
        {
            Capability.ai_advisor_basic,
            Capability.ai_evidence_basic,
        }
    ),
    ProductBundle.ai_governance_evidence: frozenset(
        {
            Capability.ai_advisor_basic,
            Capability.ai_evidence_basic,
            Capability.grc_records,
            Capability.ai_system_inventory,
            Capability.kanzlei_reports,
        }
    ),
    ProductBundle.enterprise_integrations: frozenset(
        {
            Capability.enterprise_integrations,
            Capability.kanzlei_reports,
        }
    ),
}

TIER_DEFAULT_BUNDLES: dict[ProductTier, frozenset[ProductBundle]] = {
    ProductTier.starter: frozenset({ProductBundle.ai_act_readiness}),
    ProductTier.pro: frozenset(
        {
            ProductBundle.ai_act_readiness,
            ProductBundle.ai_governance_evidence,
        }
    ),
    ProductTier.enterprise: frozenset(
        {
            ProductBundle.ai_act_readiness,
            ProductBundle.ai_governance_evidence,
            ProductBundle.enterprise_integrations,
        }
    ),
}


class TenantPlanConfig(BaseModel):
    """Product plan assigned to a tenant."""

    tenant_id: str
    tier: ProductTier = ProductTier.starter
    bundles: set[str] = Field(default_factory=set)
    label: str = ""

    def effective_bundles(self) -> set[ProductBundle]:
        """Bundles from tier defaults merged with explicit overrides."""
        result = set(TIER_DEFAULT_BUNDLES.get(self.tier, set()))
        for b in self.bundles:
            try:
                result.add(ProductBundle(b))
            except ValueError:
                pass
        return result

    def capabilities(self) -> set[Capability]:
        """All capabilities granted by the effective bundle set."""
        caps: set[Capability] = set()
        for bundle in self.effective_bundles():
            caps |= BUNDLE_CAPABILITIES.get(bundle, frozenset())
        return caps

    def has_capability(self, cap: Capability) -> bool:
        return cap in self.capabilities()

    def plan_display(self) -> str:
        """Human-readable plan string for UI (German-friendly)."""
        from app.product.copy_de import BUNDLE_LABELS_DE, TIER_LABELS_DE

        tier_label = TIER_LABELS_DE.get(self.tier.value, self.tier.value)
        bundle_names = sorted(
            BUNDLE_LABELS_DE.get(b.value, b.value) for b in self.effective_bundles()
        )
        return f"{tier_label} – {', '.join(bundle_names)}"


CAPABILITY_LABELS: dict[Capability, dict[str, str]] = {
    Capability.ai_advisor_basic: {
        "de": "AI Act Advisor (Basis)",
        "en": "AI Act Advisor (Basic)",
    },
    Capability.ai_evidence_basic: {
        "de": "AI Act Evidence & Nachweise",
        "en": "AI Act Evidence & Documentation",
    },
    Capability.grc_records: {
        "de": "GRC-Einträge (Risiko, NIS2, ISO 42001)",
        "en": "GRC Records (Risk, NIS2, ISO 42001)",
    },
    Capability.ai_system_inventory: {
        "de": "AI-System-Inventar & Lifecycle",
        "en": "AI System Inventory & Lifecycle",
    },
    Capability.kanzlei_reports: {
        "de": "Mandanten-Board-Reports & Dossiers",
        "en": "Client Board Reports & Dossiers",
    },
    Capability.enterprise_integrations: {
        "de": "Enterprise-Integrationen (SAP/DATEV)",
        "en": "Enterprise Integrations (SAP/DATEV)",
    },
}
