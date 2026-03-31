"""Cross-framework mapping skeleton — declarative mapping between GRC
entities and regulatory articles / control IDs.

This is a *structuring* layer, not a certification engine.  It shows which
frameworks and controls are *touched* by existing evidence, without
auto-certifying compliance.

Mapping data is deliberately kept as plain dicts so it can later be
externalised to YAML/JSON config files without code changes.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# EU AI Act — risk assessment fields → articles
# ---------------------------------------------------------------------------

AI_ACT_FIELD_TO_ARTICLES: dict[str, list[str]] = {
    "risk_category": ["Art. 6", "Art. 52"],
    "high_risk_likelihood": ["Art. 6(1)", "Art. 6(2)"],
    "annex_iii_category": ["Annex III"],
    "conformity_assessment_required": ["Art. 43"],
    "use_case_type": ["Art. 6(2)", "Annex III"],
}

AI_ACT_RISK_CATEGORY_ARTICLES: dict[str, list[str]] = {
    "high_risk": [
        "Art. 6",
        "Art. 8",
        "Art. 9",
        "Art. 10",
        "Art. 11",
        "Art. 12",
        "Art. 13",
        "Art. 14",
        "Art. 15",
        "Art. 43",
    ],
    "limited_risk": ["Art. 52"],
    "minimal_risk": ["Art. 69"],
    "unclassified": [],
}

# ---------------------------------------------------------------------------
# NIS2 — obligation fields → articles / entity types
# ---------------------------------------------------------------------------

NIS2_FIELD_TO_ARTICLES: dict[str, list[str]] = {
    "nis2_entity_type": ["Art. 2", "Art. 3", "Annex I", "Annex II"],
    "obligation_tags": ["Art. 21"],
    "reporting_deadlines": ["Art. 23"],
    "entity_role": ["Art. 2(1)"],
    "sector": ["Annex I", "Annex II"],
}

NIS2_OBLIGATION_TAG_ARTICLES: dict[str, list[str]] = {
    "incident_reporting": ["Art. 23(1)", "Art. 23(4)"],
    "risk_management": ["Art. 21(1)", "Art. 21(2)"],
    "supply_chain": ["Art. 21(2)(d)"],
    "bcm": ["Art. 21(2)(c)"],
    "governance": ["Art. 20"],
    "registration": ["Art. 27"],
}

# ---------------------------------------------------------------------------
# ISO 42001 — gap fields → Annex A control IDs
# ---------------------------------------------------------------------------

ISO42001_FIELD_TO_CONTROLS: dict[str, list[str]] = {
    "control_families": ["A.2", "A.3", "A.4", "A.5", "A.6"],
    "gap_severity": ["6.1", "8.1"],
    "iso27001_overlap": ["A.5 (ISO 27001 overlap)"],
}

ISO42001_CONTROL_FAMILY_IDS: dict[str, list[str]] = {
    "governance": ["A.2.2", "A.2.3", "A.2.4"],
    "risk": ["A.3.2", "A.3.3", "A.3.4"],
    "data": ["A.4.2", "A.4.3", "A.4.5", "A.4.6"],
    "monitoring": ["A.5.3", "A.5.4", "A.5.5"],
    "lifecycle": ["A.6.2", "A.6.3", "A.6.5"],
    "transparency": ["A.4.4", "A.5.2"],
}

# ---------------------------------------------------------------------------
# ISO 27001 — optional overlay where ISO 42001 controls map
# ---------------------------------------------------------------------------

ISO42001_TO_ISO27001: dict[str, list[str]] = {
    "governance": ["A.5.1", "A.5.2", "A.5.3"],
    "risk": ["A.8.2", "A.8.3"],
    "data": ["A.8.10", "A.8.24"],
    "monitoring": ["A.8.15", "A.8.16"],
    "lifecycle": ["A.8.25", "A.8.26", "A.8.27"],
    "transparency": ["A.5.37"],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def touched_controls_for_risk(
    risk_category: str,
    *,
    annex_iii_category: str = "",
    use_case_type: str = "",
) -> dict[str, list[str]]:
    """Return EU AI Act articles touched by an AiRiskAssessment."""
    articles = list(AI_ACT_RISK_CATEGORY_ARTICLES.get(risk_category, []))
    if annex_iii_category:
        articles.append("Annex III")
    if use_case_type:
        articles.extend(AI_ACT_FIELD_TO_ARTICLES.get("use_case_type", []))
    return {"eu_ai_act": sorted(set(articles))}


def touched_controls_for_nis2(
    obligation_tags: list[str],
    *,
    nis2_entity_type: str = "",
) -> dict[str, list[str]]:
    """Return NIS2 articles touched by a Nis2ObligationRecord."""
    articles: list[str] = []
    if nis2_entity_type:
        articles.extend(NIS2_FIELD_TO_ARTICLES.get("nis2_entity_type", []))
    for tag in obligation_tags:
        articles.extend(NIS2_OBLIGATION_TAG_ARTICLES.get(tag, []))
    return {"nis2": sorted(set(articles))}


def touched_controls_for_gap(
    control_families: list[str],
    *,
    iso27001_overlap: bool | None = None,
) -> dict[str, list[str]]:
    """Return ISO 42001 + ISO 27001 controls touched by a gap record."""
    iso42001: list[str] = []
    iso27001: list[str] = []
    for fam in control_families:
        iso42001.extend(ISO42001_CONTROL_FAMILY_IDS.get(fam, []))
        if iso27001_overlap:
            iso27001.extend(ISO42001_TO_ISO27001.get(fam, []))
    result: dict[str, list[str]] = {"iso42001": sorted(set(iso42001))}
    if iso27001:
        result["iso27001"] = sorted(set(iso27001))
    return result


def aggregate_framework_coverage(
    *,
    risk_categories: list[str] | None = None,
    obligation_tags: list[list[str]] | None = None,
    gap_control_families: list[list[str]] | None = None,
    has_iso27001_overlap: bool = False,
) -> dict[str, list[str]]:
    """Aggregate all framework coverage for one AiSystem.

    Returns a dict keyed by framework name with lists of unique
    articles/controls that have *some* evidence.
    """
    merged: dict[str, set[str]] = {}

    for cat in risk_categories or []:
        for fw, arts in touched_controls_for_risk(cat).items():
            merged.setdefault(fw, set()).update(arts)

    for tags in obligation_tags or []:
        for fw, arts in touched_controls_for_nis2(tags).items():
            merged.setdefault(fw, set()).update(arts)

    for families in gap_control_families or []:
        for fw, arts in touched_controls_for_gap(
            families, iso27001_overlap=has_iso27001_overlap
        ).items():
            merged.setdefault(fw, set()).update(arts)

    return {fw: sorted(arts) for fw, arts in merged.items()}


def build_system_overview_hints(
    *,
    risks: list[Any],
    nis2_records: list[Any],
    gap_records: list[Any],
) -> dict[str, list[str]]:
    """Convenience wrapper that accepts actual GRC record lists and returns
    framework coverage for an AiSystem overview API response."""
    risk_cats = [r.risk_category for r in risks]
    obligation_tags = [r.obligation_tags for r in nis2_records]
    gap_families = [g.control_families for g in gap_records]
    has_27001 = any(g.iso27001_overlap for g in gap_records if g.iso27001_overlap)
    return aggregate_framework_coverage(
        risk_categories=risk_cats,
        obligation_tags=obligation_tags,
        gap_control_families=gap_families,
        has_iso27001_overlap=has_27001,
    )
