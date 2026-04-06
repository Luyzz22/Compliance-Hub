"""Tests for Wave 18 — Offerings, GTM alignment, demo data seeding.

Covers:
- SKU definitions and catalog completeness
- SKU → tier/bundle/capability mapping
- German copy catalog (value hints, error copy)
- Persona-based demo data seeding
- Enhanced 403 error detail (upgrade hints, contact CTA)
- Value hints API filtering by plan
- Screen-view telemetry logging
- Workspace meta SKU fields
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.product.copy_de import (
    BUNDLE_DESCRIPTIONS_DE,
    BUNDLE_LABELS_DE,
    CAPABILITY_UPGRADE_HINTS_DE,
    FEATURE_NOT_ENABLED_DISCLAIMER_DE,
    TIER_DESCRIPTIONS_DE,
    TIER_LABELS_DE,
    VALUE_HINTS_DE,
)
from app.product.demo_plans import list_profiles, seed_demo_data, seed_demo_plan
from app.product.models import Capability, ProductBundle, ProductTier, TenantPlanConfig
from app.product.offerings import (
    SKU_AI_ACT_STARTER,
    SKU_CATALOG,
    SKU_ENTERPRISE_CONNECT,
    SKU_GOVERNANCE_PRO,
    get_sku,
    list_skus,
    sku_for_tier,
)
from app.product.plan_store import (
    clear_for_tests,
    has_capability,
    require_capability,
    set_tenant_plan,
)
from app.services.rag.evidence_store import (
    clear_for_tests as clear_events,
)
from app.services.rag.evidence_store import (
    list_all_events,
)


def _cleanup() -> None:
    clear_for_tests()
    clear_events()
    from app.grc.store import clear_for_tests as clear_grc

    clear_grc()


# =========================================================================
# A) SKU Catalog
# =========================================================================


class TestSKUCatalog:
    def test_catalog_has_three_skus(self) -> None:
        assert len(SKU_CATALOG) == 3

    def test_list_skus_returns_all(self) -> None:
        skus = list_skus()
        ids = {s.sku_id for s in skus}
        assert ids == {"SKU_AI_ACT_STARTER", "SKU_GOVERNANCE_PRO", "SKU_ENTERPRISE_CONNECT"}

    def test_get_sku_by_id(self) -> None:
        sku = get_sku("SKU_AI_ACT_STARTER")
        assert sku is not None
        assert sku.name_de == "AI Act Readiness"

    def test_get_sku_unknown(self) -> None:
        assert get_sku("SKU_NONEXISTENT") is None

    def test_sku_for_tier_starter(self) -> None:
        sku = sku_for_tier(ProductTier.starter)
        assert sku is not None
        assert sku.sku_id == "SKU_AI_ACT_STARTER"

    def test_sku_for_tier_pro(self) -> None:
        sku = sku_for_tier(ProductTier.pro)
        assert sku is not None
        assert sku.sku_id == "SKU_GOVERNANCE_PRO"

    def test_sku_for_tier_enterprise(self) -> None:
        sku = sku_for_tier(ProductTier.enterprise)
        assert sku is not None
        assert sku.sku_id == "SKU_ENTERPRISE_CONNECT"


# =========================================================================
# B) SKU → Tier/Bundle/Capability mapping
# =========================================================================


class TestSKUMapping:
    def test_starter_sku_maps_to_starter_tier(self) -> None:
        assert SKU_AI_ACT_STARTER.tier == ProductTier.starter

    def test_governance_pro_maps_to_pro_tier(self) -> None:
        assert SKU_GOVERNANCE_PRO.tier == ProductTier.pro

    def test_enterprise_connect_maps_to_enterprise(self) -> None:
        assert SKU_ENTERPRISE_CONNECT.tier == ProductTier.enterprise

    def test_starter_sku_creates_valid_plan(self) -> None:
        plan = SKU_AI_ACT_STARTER.to_plan("t1")
        assert plan.tier == ProductTier.starter
        assert plan.has_capability(Capability.ai_advisor_basic)
        assert not plan.has_capability(Capability.grc_records)

    def test_governance_sku_creates_valid_plan(self) -> None:
        plan = SKU_GOVERNANCE_PRO.to_plan("t2")
        assert plan.tier == ProductTier.pro
        assert plan.has_capability(Capability.grc_records)
        assert plan.has_capability(Capability.kanzlei_reports)
        assert not plan.has_capability(Capability.enterprise_integrations)

    def test_enterprise_sku_creates_valid_plan(self) -> None:
        plan = SKU_ENTERPRISE_CONNECT.to_plan("t3")
        assert plan.tier == ProductTier.enterprise
        for cap in Capability:
            assert plan.has_capability(cap), f"Missing {cap}"

    def test_all_skus_have_german_description(self) -> None:
        for sku in list_skus():
            assert sku.name_de, f"{sku.sku_id} missing name_de"
            assert sku.description_de, f"{sku.sku_id} missing description_de"
            assert sku.tagline_de, f"{sku.sku_id} missing tagline_de"
            assert sku.target_segment_de, f"{sku.sku_id} missing target_segment_de"

    def test_all_skus_have_use_cases(self) -> None:
        for sku in list_skus():
            assert len(sku.use_cases_de) >= 2, f"{sku.sku_id} needs >= 2 use cases"

    def test_all_skus_have_demo_profile(self) -> None:
        for sku in list_skus():
            assert sku.demo_profile, f"{sku.sku_id} missing demo_profile"


# =========================================================================
# C) German copy catalog
# =========================================================================


class TestGermanCopy:
    def test_tier_labels_complete(self) -> None:
        for tier in ProductTier:
            assert tier.value in TIER_LABELS_DE

    def test_tier_descriptions_complete(self) -> None:
        for tier in ProductTier:
            assert tier.value in TIER_DESCRIPTIONS_DE
            assert len(TIER_DESCRIPTIONS_DE[tier.value]) > 20

    def test_bundle_labels_complete(self) -> None:
        for bundle in ProductBundle:
            assert bundle.value in BUNDLE_LABELS_DE

    def test_bundle_descriptions_complete(self) -> None:
        for bundle in ProductBundle:
            assert bundle.value in BUNDLE_DESCRIPTIONS_DE
            assert len(BUNDLE_DESCRIPTIONS_DE[bundle.value]) > 20

    def test_value_hints_exist_for_key_screens(self) -> None:
        required_screens = [
            "ai_advisor",
            "evidence_views",
            "grc_records",
            "ai_system_inventory",
            "kanzlei_reports",
            "kanzlei_dossier",
            "enterprise_integrations",
        ]
        for screen in required_screens:
            assert screen in VALUE_HINTS_DE, f"Missing hint for {screen}"
            assert "Teil" in VALUE_HINTS_DE[screen]

    def test_value_hints_no_compliance_guarantees(self) -> None:
        forbidden = ["garantiert", "vollständige Konformität", "rechtskonform"]
        for key, text in VALUE_HINTS_DE.items():
            for word in forbidden:
                assert word.lower() not in text.lower(), (
                    f"Hint '{key}' contains forbidden claim: {word}"
                )

    def test_upgrade_hints_for_all_capabilities(self) -> None:
        for cap in Capability:
            assert cap in CAPABILITY_UPGRADE_HINTS_DE, f"Missing upgrade hint for {cap}"

    def test_disclaimer_present(self) -> None:
        assert "Rechtsberatung" in FEATURE_NOT_ENABLED_DISCLAIMER_DE
        assert "unterstützt" in FEATURE_NOT_ENABLED_DISCLAIMER_DE


# =========================================================================
# D) Enhanced 403 error detail
# =========================================================================


class TestEnhancedError403:
    def test_error_includes_upgrade_hint(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t-err", tier=ProductTier.starter))
        with pytest.raises(HTTPException) as exc:
            require_capability("t-err", Capability.grc_records)
        detail = exc.value.detail
        assert "upgrade_hint_de" in detail
        assert "Professional" in detail["upgrade_hint_de"]

    def test_error_includes_contact_cta(self) -> None:
        _cleanup()
        with pytest.raises(HTTPException) as exc:
            require_capability("t-new", Capability.enterprise_integrations)
        detail = exc.value.detail
        assert "contact_cta_de" in detail
        assert "kontakt@compliancehub.de" in detail["contact_cta_de"]
        assert detail["contact_url"] == "mailto:kontakt@compliancehub.de"

    def test_error_includes_disclaimer(self) -> None:
        _cleanup()
        with pytest.raises(HTTPException) as exc:
            require_capability("t-new2", Capability.grc_records)
        detail = exc.value.detail
        assert "disclaimer_de" in detail
        assert "Rechtsberatung" in detail["disclaimer_de"]

    def test_error_includes_current_plan(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t-plan", tier=ProductTier.starter))
        with pytest.raises(HTTPException) as exc:
            require_capability("t-plan", Capability.kanzlei_reports)
        detail = exc.value.detail
        assert "current_plan" in detail
        assert "Starter" in detail["current_plan"]


# =========================================================================
# E) Demo data seeding
# =========================================================================


class TestDemoDataSeeding:
    def test_seed_industrie_creates_systems(self) -> None:
        _cleanup()
        result = seed_demo_data("t-seed-ind", "industrie_mittelstand_demo")
        assert result["ai_systems"] == 3
        assert result["risks"] == 3

    def test_seed_kanzlei_creates_systems(self) -> None:
        _cleanup()
        result = seed_demo_data("t-seed-kz", "kanzlei_demo")
        assert result["ai_systems"] == 3
        assert result["risks"] == 3

    def test_seed_sap_creates_systems(self) -> None:
        _cleanup()
        result = seed_demo_data("t-seed-sap", "sap_enterprise_demo")
        assert result["ai_systems"] == 3
        assert result["risks"] == 3
        assert result["nis2"] >= 2

    def test_seed_sme_creates_systems(self) -> None:
        _cleanup()
        result = seed_demo_data("t-seed-sme", "sme_demo")
        assert result["ai_systems"] == 2

    def test_seed_unknown_profile_uses_default(self) -> None:
        _cleanup()
        result = seed_demo_data("t-seed-unk", "nonexistent_profile")
        assert result["ai_systems"] >= 2

    def test_seed_emits_evidence_event(self) -> None:
        _cleanup()
        seed_demo_data("t-seed-ev", "kanzlei_demo")
        events = list_all_events()
        seed_events = [e for e in events if e.get("event_type") == "demo_data_seeded"]
        assert len(seed_events) == 1
        assert seed_events[0]["profile"] == "kanzlei_demo"

    def test_full_demo_seed_plan_plus_data(self) -> None:
        _cleanup()
        plan = seed_demo_plan("t-full", "sap_enterprise_demo")
        assert plan is not None
        assert plan.tier == ProductTier.enterprise
        result = seed_demo_data("t-full", "sap_enterprise_demo")
        assert result["ai_systems"] >= 2
        assert has_capability("t-full", Capability.enterprise_integrations)

    def test_demo_mode_activation_event(self) -> None:
        _cleanup()
        seed_demo_plan("t-ev-dm", "industrie_mittelstand_demo")
        events = list_all_events()
        dm_events = [e for e in events if e.get("event_type") == "demo_mode_activated"]
        assert len(dm_events) == 1
        assert dm_events[0]["profile"] == "industrie_mittelstand_demo"

    def test_four_demo_profiles_available(self) -> None:
        profiles = list_profiles()
        assert len(profiles) == 4
        assert set(profiles) == {
            "industrie_mittelstand_demo",
            "kanzlei_demo",
            "sap_enterprise_demo",
            "sme_demo",
        }


# =========================================================================
# F) Telemetry / GTM events
# =========================================================================


class TestGTMTelemetry:
    def test_screen_view_event_structure(self) -> None:
        from app.services.rag.evidence_store import record_event

        _cleanup()
        record_event(
            {
                "event_type": "gtm_screen_view",
                "tenant_id": "t-tel",
                "screen": "ai_system_inventory",
                "demo_profile": "kanzlei_demo",
                "plan_tier": "pro",
            }
        )
        events = list_all_events()
        sv_events = [e for e in events if e.get("event_type") == "gtm_screen_view"]
        assert len(sv_events) == 1
        assert sv_events[0]["screen"] == "ai_system_inventory"
        assert sv_events[0]["plan_tier"] == "pro"


# =========================================================================
# G) Workspace meta SKU fields
# =========================================================================


class TestWorkspaceMetaSKU:
    def test_sku_for_starter_returns_ai_act_readiness(self) -> None:
        sku = sku_for_tier(ProductTier.starter)
        assert sku is not None
        assert sku.name_de == "AI Act Readiness"
        assert sku.tagline_de != ""

    def test_sku_for_pro_returns_governance(self) -> None:
        sku = sku_for_tier(ProductTier.pro)
        assert sku is not None
        assert "Governance" in sku.name_de

    def test_plan_display_uses_german_labels(self) -> None:
        plan = TenantPlanConfig(tenant_id="t-disp", tier=ProductTier.pro)
        display = plan.plan_display()
        assert "Professional" in display
        assert "AI Governance & Evidence" in display
