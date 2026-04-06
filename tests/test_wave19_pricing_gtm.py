"""Wave 19 — internal pricing & sales config sanity checks."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from app.product.copy_de import CAPABILITY_UPGRADE_HINTS_DE, VALUE_HINTS_DE
from app.product.models import Capability

_DOCS_GTM = Path(__file__).resolve().parent.parent / "docs" / "gtm"


def test_pricing_internal_yaml_loads() -> None:
    path = _DOCS_GTM / "pricing_internal.yaml"
    assert path.is_file()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data.get("version")
    assert data.get("entries")
    for row in data["entries"]:
        assert "sku" in row
        assert "segment" in row
        assert row["positioning"] in ("entry", "core", "premium_addon")
        assert "relative_price" in row
        assert "billing_model_hint" in row


def test_sales_arguments_json_structure() -> None:
    path = _DOCS_GTM / "sales_arguments_by_segment.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    skus = ["SKU_AI_ACT_STARTER", "SKU_GOVERNANCE_PRO", "SKU_ENTERPRISE_CONNECT"]
    segments = ["kmu_industrie_mittelstand", "kanzlei", "enterprise_sap"]
    for sku in skus:
        assert sku in data
        for seg in segments:
            block = data[sku][seg]
            args = block["arguments_de"]
            assert 3 <= len(args) <= 6
            joined = " ".join(args).lower()
            assert "garantiert" not in joined
            assert "vollständige konformität" not in joined


def test_lead_heuristics_json_loads() -> None:
    path = _DOCS_GTM / "lead_to_package_heuristics.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["qualification_questions"]
    assert data["routing_heuristics"]
    assert data["answer_hints_to_packages"]


def test_playbook_and_cheat_sheet_exist() -> None:
    assert (_DOCS_GTM / "wave19-internal-pricing-and-sales-playbook.md").is_file()
    assert (_DOCS_GTM / "sales_enablement_cheat_sheet.md").is_file()


def test_value_hints_include_tier_positioning() -> None:
    assert "Starter-Tier" in VALUE_HINTS_DE["ai_advisor"]
    assert "Professional-Tier" in VALUE_HINTS_DE["grc_records"]
    assert "Zusatzpaket" in VALUE_HINTS_DE["enterprise_integrations"]
    assert "SAP-/DATEV" in VALUE_HINTS_DE["enterprise_integrations"]


def test_upgrade_hints_reference_tiers() -> None:
    assert "Starter-Tier" in CAPABILITY_UPGRADE_HINTS_DE[Capability.ai_advisor_basic]
    assert "Professional-Tier" in CAPABILITY_UPGRADE_HINTS_DE[Capability.grc_records]
    assert "Enterprise-Tier" in CAPABILITY_UPGRADE_HINTS_DE[Capability.enterprise_integrations]
