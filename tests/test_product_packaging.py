"""Tests for Wave 17 — Product packaging & feature-flag model.

Covers:
- Tier/bundle/capability model resolution
- TenantPlanConfig capability checks
- Plan store CRUD and defaults
- API capability enforcement (403 on missing capability)
- Demo plan profiles
- Usage metrics logging
- Workspace meta plan fields
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.product.demo_plans import list_profiles, seed_demo_plan
from app.product.models import (
    BUNDLE_CAPABILITIES,
    TIER_DEFAULT_BUNDLES,
    Capability,
    ProductBundle,
    ProductTier,
    TenantPlanConfig,
)
from app.product.plan_store import (
    clear_for_tests,
    get_tenant_plan,
    has_capability,
    log_capability_usage,
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


# =========================================================================
# A) Model: Tier → Bundles → Capabilities
# =========================================================================


class TestTierBundleModel:
    def test_starter_tier_has_ai_act_readiness(self) -> None:
        assert ProductBundle.ai_act_readiness in TIER_DEFAULT_BUNDLES[ProductTier.starter]

    def test_pro_tier_has_governance_and_readiness(self) -> None:
        pro_bundles = TIER_DEFAULT_BUNDLES[ProductTier.pro]
        assert ProductBundle.ai_act_readiness in pro_bundles
        assert ProductBundle.ai_governance_evidence in pro_bundles

    def test_enterprise_tier_has_all_bundles(self) -> None:
        ent = TIER_DEFAULT_BUNDLES[ProductTier.enterprise]
        assert ProductBundle.ai_act_readiness in ent
        assert ProductBundle.ai_governance_evidence in ent
        assert ProductBundle.enterprise_integrations in ent

    def test_ai_act_readiness_grants_advisor_and_evidence(self) -> None:
        caps = BUNDLE_CAPABILITIES[ProductBundle.ai_act_readiness]
        assert Capability.ai_advisor_basic in caps
        assert Capability.ai_evidence_basic in caps

    def test_governance_evidence_grants_grc_and_inventory(self) -> None:
        caps = BUNDLE_CAPABILITIES[ProductBundle.ai_governance_evidence]
        assert Capability.grc_records in caps
        assert Capability.ai_system_inventory in caps
        assert Capability.kanzlei_reports in caps

    def test_enterprise_integrations_grants_connectors(self) -> None:
        caps = BUNDLE_CAPABILITIES[ProductBundle.enterprise_integrations]
        assert Capability.enterprise_integrations in caps
        assert Capability.kanzlei_reports in caps


# =========================================================================
# B) TenantPlanConfig resolution
# =========================================================================


class TestTenantPlanConfig:
    def test_starter_effective_bundles(self) -> None:
        plan = TenantPlanConfig(tenant_id="t1", tier=ProductTier.starter)
        bundles = plan.effective_bundles()
        assert ProductBundle.ai_act_readiness in bundles
        assert ProductBundle.enterprise_integrations not in bundles

    def test_starter_capabilities(self) -> None:
        plan = TenantPlanConfig(tenant_id="t1", tier=ProductTier.starter)
        caps = plan.capabilities()
        assert Capability.ai_advisor_basic in caps
        assert Capability.ai_evidence_basic in caps
        assert Capability.grc_records not in caps
        assert Capability.enterprise_integrations not in caps

    def test_pro_capabilities(self) -> None:
        plan = TenantPlanConfig(tenant_id="t1", tier=ProductTier.pro)
        caps = plan.capabilities()
        assert Capability.ai_advisor_basic in caps
        assert Capability.grc_records in caps
        assert Capability.ai_system_inventory in caps
        assert Capability.kanzlei_reports in caps
        assert Capability.enterprise_integrations not in caps

    def test_enterprise_capabilities(self) -> None:
        plan = TenantPlanConfig(tenant_id="t1", tier=ProductTier.enterprise)
        caps = plan.capabilities()
        for cap in Capability:
            assert cap in caps, f"Enterprise missing {cap}"

    def test_explicit_bundle_override(self) -> None:
        plan = TenantPlanConfig(
            tenant_id="t1",
            tier=ProductTier.starter,
            bundles={"enterprise_integrations"},
        )
        caps = plan.capabilities()
        assert Capability.enterprise_integrations in caps
        assert Capability.ai_advisor_basic in caps

    def test_has_capability_method(self) -> None:
        plan = TenantPlanConfig(tenant_id="t1", tier=ProductTier.pro)
        assert plan.has_capability(Capability.grc_records)
        assert not plan.has_capability(Capability.enterprise_integrations)

    def test_plan_display_string(self) -> None:
        plan = TenantPlanConfig(tenant_id="t1", tier=ProductTier.pro)
        display = plan.plan_display()
        assert "Professional" in display
        assert "AI Act Readiness" in display
        assert "AI Governance" in display


# =========================================================================
# C) Plan store
# =========================================================================


class TestPlanStore:
    def test_default_plan_is_starter(self) -> None:
        _cleanup()
        plan = get_tenant_plan("unknown-tenant")
        assert plan.tier == ProductTier.starter

    def test_set_and_get_plan(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t1", tier=ProductTier.enterprise))
        plan = get_tenant_plan("t1")
        assert plan.tier == ProductTier.enterprise
        assert has_capability("t1", Capability.enterprise_integrations)

    def test_has_capability_fast_path(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t2", tier=ProductTier.starter))
        assert has_capability("t2", Capability.ai_advisor_basic)
        assert not has_capability("t2", Capability.grc_records)

    def test_require_capability_passes(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t3", tier=ProductTier.pro))
        require_capability("t3", Capability.grc_records)

    def test_require_capability_raises_403(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t4", tier=ProductTier.starter))
        with pytest.raises(HTTPException) as exc:
            require_capability("t4", Capability.enterprise_integrations)
        assert exc.value.status_code == 403
        detail = exc.value.detail
        assert detail["error"] == "feature_not_enabled"
        assert "message_de" in detail
        assert "message_en" in detail
        assert "Paket" in detail["message_de"]
        assert "ComplianceHub" in detail["message_en"]
        assert "upgrade_hint_de" in detail
        assert "contact_cta_de" in detail
        assert "contact_url" in detail
        assert "disclaimer_de" in detail
        assert "current_plan" in detail

    def test_require_capability_includes_capability_name(self) -> None:
        _cleanup()
        with pytest.raises(HTTPException) as exc:
            require_capability("new-tenant", Capability.grc_records)
        assert exc.value.detail["capability"] == "cap_grc_records"


# =========================================================================
# D) Demo plan profiles
# =========================================================================


class TestDemoProfiles:
    def test_list_profiles(self) -> None:
        profiles = list_profiles()
        assert "kanzlei_demo" in profiles
        assert "sap_enterprise_demo" in profiles
        assert "sme_demo" in profiles
        assert "industrie_mittelstand_demo" in profiles

    def test_seed_kanzlei_demo(self) -> None:
        _cleanup()
        plan = seed_demo_plan("t-kanzlei", "kanzlei_demo")
        assert plan is not None
        assert plan.tier == ProductTier.pro
        assert has_capability("t-kanzlei", Capability.kanzlei_reports)
        assert has_capability("t-kanzlei", Capability.grc_records)
        assert not has_capability("t-kanzlei", Capability.enterprise_integrations)

    def test_seed_sap_enterprise_demo(self) -> None:
        _cleanup()
        plan = seed_demo_plan("t-sap", "sap_enterprise_demo")
        assert plan is not None
        assert plan.tier == ProductTier.enterprise
        assert has_capability("t-sap", Capability.enterprise_integrations)
        assert has_capability("t-sap", Capability.grc_records)
        assert has_capability("t-sap", Capability.ai_advisor_basic)

    def test_seed_industrie_mittelstand_demo(self) -> None:
        _cleanup()
        plan = seed_demo_plan("t-ind", "industrie_mittelstand_demo")
        assert plan is not None
        assert plan.tier == ProductTier.pro
        assert has_capability("t-ind", Capability.grc_records)
        assert has_capability("t-ind", Capability.ai_system_inventory)
        assert not has_capability("t-ind", Capability.enterprise_integrations)

    def test_seed_sme_demo(self) -> None:
        _cleanup()
        plan = seed_demo_plan("t-sme", "sme_demo")
        assert plan is not None
        assert plan.tier == ProductTier.starter
        assert has_capability("t-sme", Capability.ai_advisor_basic)
        assert not has_capability("t-sme", Capability.grc_records)

    def test_seed_unknown_profile(self) -> None:
        _cleanup()
        plan = seed_demo_plan("t-x", "nonexistent")
        assert plan is None


# =========================================================================
# E) Usage metrics
# =========================================================================


class TestUsageMetrics:
    def test_log_capability_usage(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t5", tier=ProductTier.pro))
        log_capability_usage(
            tenant_id="t5",
            capability="cap_grc_records",
            action="list_risks",
        )
        events = list_all_events()
        usage_events = [e for e in events if e.get("event_type") == "capability_usage"]
        assert len(usage_events) == 1
        ev = usage_events[0]
        assert ev["tenant_id"] == "t5"
        assert ev["capability"] == "cap_grc_records"
        assert ev["action"] == "list_risks"
        assert ev["tier"] == "pro"
        assert ev["bundle"] != ""

    def test_log_capability_usage_with_explicit_bundle(self) -> None:
        _cleanup()
        log_capability_usage(
            tenant_id="t6",
            capability="cap_ai_advisor_basic",
            action="query",
            bundle="ai_act_readiness",
        )
        events = list_all_events()
        usage_events = [e for e in events if e.get("event_type") == "capability_usage"]
        assert len(usage_events) == 1
        assert usage_events[0]["bundle"] == "ai_act_readiness"


# =========================================================================
# F) Capability enforcement scenarios
# =========================================================================


class TestCapabilityEnforcement:
    def test_starter_cannot_access_grc(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t-starter", tier=ProductTier.starter))
        with pytest.raises(HTTPException) as exc:
            require_capability("t-starter", Capability.grc_records)
        assert exc.value.status_code == 403

    def test_starter_can_access_evidence(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t-starter", tier=ProductTier.starter))
        require_capability("t-starter", Capability.ai_evidence_basic)

    def test_pro_cannot_access_integrations(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t-pro", tier=ProductTier.pro))
        with pytest.raises(HTTPException):
            require_capability("t-pro", Capability.enterprise_integrations)

    def test_enterprise_can_access_everything(self) -> None:
        _cleanup()
        set_tenant_plan(TenantPlanConfig(tenant_id="t-ent", tier=ProductTier.enterprise))
        for cap in Capability:
            require_capability("t-ent", cap)

    def test_addon_bundle_extends_starter(self) -> None:
        _cleanup()
        set_tenant_plan(
            TenantPlanConfig(
                tenant_id="t-custom",
                tier=ProductTier.starter,
                bundles={"ai_governance_evidence"},
            )
        )
        assert has_capability("t-custom", Capability.grc_records)
        assert has_capability("t-custom", Capability.ai_system_inventory)
        assert not has_capability("t-custom", Capability.enterprise_integrations)
