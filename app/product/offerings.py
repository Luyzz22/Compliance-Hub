"""Concrete offering definitions (SKUs) for DACH GTM.

Each SKU maps to a tier + bundles and carries German-language
copy for sales, demos, and in-app messaging.  SKUs are the
customer-facing names; tiers/bundles/capabilities stay internal.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.product.models import (
    ProductBundle,
    ProductTier,
    TenantPlanConfig,
)


class OfferingSKU(BaseModel):
    """A named, sellable product offering."""

    sku_id: str
    name_de: str
    name_en: str
    tagline_de: str = ""
    description_de: str = ""
    target_segment_de: str = ""
    tier: ProductTier = ProductTier.starter
    bundles: list[str] = Field(default_factory=list)
    use_cases_de: list[str] = Field(default_factory=list)
    demo_profile: str = ""

    def to_plan(self, tenant_id: str) -> TenantPlanConfig:
        return TenantPlanConfig(
            tenant_id=tenant_id,
            tier=self.tier,
            bundles=set(self.bundles),
            label=self.name_de,
        )


# ---------------------------------------------------------------------------
# SKU catalog
# ---------------------------------------------------------------------------

SKU_AI_ACT_STARTER = OfferingSKU(
    sku_id="SKU_AI_ACT_STARTER",
    name_de="AI Act Readiness",
    name_en="AI Act Readiness",
    tagline_de="Der schnelle Einstieg in die KI-Verordnung.",
    description_de=(
        "Unterstützt KMU und Kanzleien beim strukturierten Einstieg in die "
        "EU-KI-Verordnung (AI Act). Enthält den AI Act Advisor für erste "
        "Risikoeinschätzungen sowie den Evidence-Bereich zur Dokumentation "
        "von Nachweisen und Prüfschritten."
    ),
    target_segment_de="KMU, Steuerberater-Kanzleien (Einstieg)",
    tier=ProductTier.starter,
    bundles=[ProductBundle.ai_act_readiness],
    use_cases_de=[
        "Erste AI-Act-Risikoeinschätzung für ein KI-System durchführen",
        "Nachweise und Dokumentation im Evidence-Bereich ablegen",
        "Überblick: Welche meiner KI-Anwendungen sind betroffen?",
    ],
    demo_profile="sme_demo",
)

SKU_GOVERNANCE_PRO = OfferingSKU(
    sku_id="SKU_GOVERNANCE_PRO",
    name_de="AI Governance & Evidence Suite",
    name_en="AI Governance & Evidence Suite",
    tagline_de="Umfassende KI-Governance für Kanzleien und Mittelstand.",
    description_de=(
        "Erweitert AI Act Readiness um vollständiges GRC-Management "
        "(Risikobewertungen, NIS2-Pflichten, ISO 42001-Gaps), ein "
        "AI-System-Inventar mit Lifecycle-Tracking sowie Mandanten-Board-Reports "
        "und Kanzlei-Compliance-Dossiers. Ideal für Steuerberater und "
        "Wirtschaftsprüfer, die ihre Mandanten ganzheitlich beraten."
    ),
    target_segment_de="Steuerberater-/WP-Kanzleien, wachsender Mittelstand",
    tier=ProductTier.pro,
    bundles=[
        ProductBundle.ai_act_readiness,
        ProductBundle.ai_governance_evidence,
    ],
    use_cases_de=[
        "KI-System-Inventar aufbauen und AI-Act-Klassifizierung pflegen",
        "NIS2-Pflichten und ISO 42001-Gaps pro System tracken",
        "Mandanten-Board-Report als Grundlage für Beirats-/Vorstandsberichte erstellen",
        "Kanzlei-Compliance-Dossier als Anlage zur Verfahrensdokumentation exportieren",
    ],
    demo_profile="kanzlei_demo",
)

SKU_ENTERPRISE_CONNECT = OfferingSKU(
    sku_id="SKU_ENTERPRISE_CONNECT",
    name_de="Enterprise Connectors (SAP/DATEV)",
    name_en="Enterprise Connectors (SAP/DATEV)",
    tagline_de="Nahtlose Integration in SAP- und DATEV-Ökosysteme.",
    description_de=(
        "Ergänzt die AI Governance Suite um Enterprise-Integrationen: "
        "DATEV-konforme Mandanten-Exporte, SAP BTP Event-Mesh-Anbindung "
        "und automatisierte Synchronisation von KI-Governance-Daten mit "
        "bestehenden Unternehmensplattformen. Für Unternehmen, die ihre "
        "KI-Compliance in vorhandene IT-Landschaften einbetten."
    ),
    target_segment_de="SAP-zentrierter Mittelstand, größere Kanzleien mit Systemintegration",
    tier=ProductTier.enterprise,
    bundles=[
        ProductBundle.ai_act_readiness,
        ProductBundle.ai_governance_evidence,
        ProductBundle.enterprise_integrations,
    ],
    use_cases_de=[
        "DATEV-konforme Compliance-Dossiers automatisch erzeugen und exportieren",
        "KI-System-Events aus SAP S/4HANA via BTP Event Mesh empfangen",
        "Integration-Jobs überwachen, wiederholen und als Audit-Trail nutzen",
    ],
    demo_profile="sap_demo",
)

SKU_CATALOG: dict[str, OfferingSKU] = {
    SKU_AI_ACT_STARTER.sku_id: SKU_AI_ACT_STARTER,
    SKU_GOVERNANCE_PRO.sku_id: SKU_GOVERNANCE_PRO,
    SKU_ENTERPRISE_CONNECT.sku_id: SKU_ENTERPRISE_CONNECT,
}


def get_sku(sku_id: str) -> OfferingSKU | None:
    return SKU_CATALOG.get(sku_id)


def list_skus() -> list[OfferingSKU]:
    return list(SKU_CATALOG.values())


def sku_for_tier(tier: ProductTier) -> OfferingSKU | None:
    """Find the primary SKU for a given tier."""
    for sku in SKU_CATALOG.values():
        if sku.tier == tier:
            return sku
    return None
