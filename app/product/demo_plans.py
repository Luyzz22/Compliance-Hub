"""Pre-configured demo tenant plans and sample data seeding.

Each plan profile represents a typical DACH customer segment:
- industrie_mittelstand_demo: Pro — CISO/AI-Owner persona
- kanzlei_demo: Pro — Kanzlei-Partner / Tax-Compliance persona
- sap_enterprise_demo: Enterprise — SAP/BTP-zentrierter Mittelstand
- sme_demo: Starter — KMU-Einstieg (AI Act Readiness only)

Demo seeding creates realistic sample data so demos can show the
full product immediately without manual setup.
"""

from __future__ import annotations

import logging
from typing import Any

from app.product.models import ProductBundle, ProductTier, TenantPlanConfig
from app.product.plan_store import set_tenant_plan
from app.services.rag.evidence_store import record_event

logger = logging.getLogger(__name__)


DEMO_PLAN_PROFILES: dict[str, TenantPlanConfig] = {
    "industrie_mittelstand_demo": TenantPlanConfig(
        tenant_id="",
        tier=ProductTier.pro,
        bundles={
            ProductBundle.ai_act_readiness,
            ProductBundle.ai_governance_evidence,
        },
        label="Industrie-Mittelstand Demo (Professional)",
    ),
    "kanzlei_demo": TenantPlanConfig(
        tenant_id="",
        tier=ProductTier.pro,
        bundles={
            ProductBundle.ai_act_readiness,
            ProductBundle.ai_governance_evidence,
        },
        label="Kanzlei Demo (Professional)",
    ),
    "sap_enterprise_demo": TenantPlanConfig(
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
        label="KMU Demo (Starter)",
    ),
}


def seed_demo_plan(tenant_id: str, profile: str) -> TenantPlanConfig | None:
    """Apply a demo plan profile to a tenant. Returns None if profile unknown."""
    template = DEMO_PLAN_PROFILES.get(profile)
    if template is None:
        return None
    plan = template.model_copy(update={"tenant_id": tenant_id})
    saved = set_tenant_plan(plan)
    record_event(
        {
            "event_type": "demo_mode_activated",
            "tenant_id": tenant_id,
            "profile": profile,
            "tier": saved.tier.value,
        }
    )
    return saved


def seed_demo_data(tenant_id: str, profile: str) -> dict[str, Any]:
    """Seed sample GRC/AiSystem data for a demo tenant.

    Returns a summary of what was created.
    """
    from app.grc.models import (
        AiRiskAssessment,
        AiSystem,
        AiSystemClassification,
        GapStatus,
        Iso42001GapRecord,
        LifecycleStage,
        Nis2ObligationRecord,
        ObligationStatus,
        ReadinessLevel,
    )
    from app.grc.store import upsert_ai_system, upsert_gap, upsert_nis2, upsert_risk

    client_id = f"demo-mandant-{profile}"
    counts: dict[str, int] = {
        "ai_systems": 0,
        "risks": 0,
        "nis2": 0,
        "gaps": 0,
    }

    systems_spec = _DEMO_SYSTEMS.get(profile, _DEMO_SYSTEMS["industrie_mittelstand_demo"])
    for spec in systems_spec:
        upsert_ai_system(
            AiSystem(
                tenant_id=tenant_id,
                client_id=client_id,
                system_id=spec["system_id"],
                name=spec["name"],
                description=spec["description"],
                business_owner=spec.get("owner", ""),
                ai_act_classification=AiSystemClassification(
                    spec.get("classification", "not_in_scope")
                ),
                lifecycle_stage=LifecycleStage(spec.get("lifecycle", "production")),
                readiness_level=ReadinessLevel(spec.get("readiness", "unknown")),
                nis2_relevant=spec.get("nis2", False),
                iso42001_in_scope=spec.get("iso42001", False),
            )
        )
        counts["ai_systems"] += 1

        upsert_risk(
            AiRiskAssessment(
                tenant_id=tenant_id,
                client_id=client_id,
                system_id=spec["system_id"],
                risk_category=spec.get("risk", "unclassified"),
                high_risk_likelihood=spec.get("risk_likelihood", "unknown"),
            )
        )
        counts["risks"] += 1

        if spec.get("nis2"):
            upsert_nis2(
                Nis2ObligationRecord(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    system_id=spec["system_id"],
                    nis2_entity_type="essential",
                    sector=spec.get("sector", ""),
                    status=ObligationStatus.identified,
                )
            )
            counts["nis2"] += 1

        if spec.get("iso42001"):
            upsert_gap(
                Iso42001GapRecord(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    system_id=spec["system_id"],
                    control_families=spec.get("gap_families", ["A.6_Planning"]),
                    gap_severity=spec.get("gap_severity", "minor"),
                    status=GapStatus(spec.get("gap_status", "open")),
                )
            )
            counts["gaps"] += 1

    logger.info(
        "demo_data_seeded",
        extra={"tenant_id": tenant_id, "profile": profile, **counts},
    )
    record_event(
        {
            "event_type": "demo_data_seeded",
            "tenant_id": tenant_id,
            "profile": profile,
            **counts,
        }
    )
    return {"tenant_id": tenant_id, "profile": profile, "client_id": client_id, **counts}


def list_profiles() -> list[str]:
    return sorted(DEMO_PLAN_PROFILES.keys())


# ---------------------------------------------------------------------------
# Sample system specs per persona
# ---------------------------------------------------------------------------

_DEMO_SYSTEMS: dict[str, list[dict[str, Any]]] = {
    "industrie_mittelstand_demo": [
        {
            "system_id": "pred-maintenance-v1",
            "name": "Predictive Maintenance Engine",
            "description": "ML-basierte Vorhersage von Maschinenausfällen in der Produktion",
            "owner": "Dr. Thomas Berger (Leiter Produktion)",
            "classification": "high_risk_candidate",
            "lifecycle": "production",
            "readiness": "partially_covered",
            "risk": "high",
            "risk_likelihood": "likely",
            "nis2": True,
            "sector": "manufacturing",
            "iso42001": True,
            "gap_families": ["A.6_Planning", "A.8_Operation"],
            "gap_severity": "major",
        },
        {
            "system_id": "quality-inspect-v2",
            "name": "Qualitätskontrolle Bildanalyse",
            "description": "KI-gestützte visuelle Qualitätsprüfung in der Fertigung",
            "owner": "Sandra Klein (Qualitätsmanagement)",
            "classification": "limited",
            "lifecycle": "testing",
            "readiness": "insufficient_evidence",
            "risk": "medium",
            "risk_likelihood": "possible",
            "iso42001": True,
            "gap_families": ["A.10_Performance"],
            "gap_severity": "minor",
            "gap_status": "remediation_planned",
        },
        {
            "system_id": "hr-screening-v1",
            "name": "Bewerber-Vorauswahl",
            "description": "Automatisierte CV-Analyse und Vorfilterung",
            "owner": "Julia Hartmann (HR)",
            "classification": "high_risk",
            "lifecycle": "pilot",
            "readiness": "insufficient_evidence",
            "risk": "high",
            "risk_likelihood": "very_likely",
        },
    ],
    "kanzlei_demo": [
        {
            "system_id": "mandant-chatbot-v1",
            "name": "Mandanten-Auskunft Chatbot",
            "description": "LLM-basierter Chatbot für Mandantenanfragen zu Steuerfristen",
            "owner": "StB Max Müller",
            "classification": "limited",
            "lifecycle": "production",
            "readiness": "partially_covered",
            "risk": "medium",
            "risk_likelihood": "possible",
        },
        {
            "system_id": "doc-classification-v1",
            "name": "Belegklassifikation",
            "description": "Automatische Zuordnung von Belegen zu Buchungskonten",
            "owner": "StBin Lisa Schmidt",
            "classification": "minimal",
            "lifecycle": "production",
            "readiness": "ready_for_review",
            "risk": "low",
            "risk_likelihood": "unlikely",
        },
        {
            "system_id": "tax-risk-scoring-v1",
            "name": "Steuerrisiko-Scoring",
            "description": "ML-basierte Einschätzung von Betriebsprüfungsrisiken",
            "owner": "WP Dr. Frank Weber",
            "classification": "high_risk_candidate",
            "lifecycle": "development",
            "readiness": "insufficient_evidence",
            "risk": "high",
            "risk_likelihood": "likely",
            "nis2": False,
            "iso42001": True,
            "gap_families": ["A.6_Planning", "A.7_Support"],
            "gap_severity": "major",
        },
    ],
    "sap_enterprise_demo": [
        {
            "system_id": "sap-credit-scoring-v1",
            "name": "SAP Kredit-Scoring Engine",
            "description": "Kreditwürdigkeitsprüfung integriert in SAP S/4HANA FI",
            "owner": "Michael Braun (CFO)",
            "classification": "high_risk",
            "lifecycle": "production",
            "readiness": "partially_covered",
            "risk": "high",
            "risk_likelihood": "very_likely",
            "nis2": True,
            "sector": "finance",
            "iso42001": True,
            "gap_families": ["A.6_Planning", "A.8_Operation", "A.10_Performance"],
            "gap_severity": "major",
        },
        {
            "system_id": "sap-fraud-detect-v1",
            "name": "SAP Fraud Detection",
            "description": "Anomalie-Erkennung in Finanztransaktionen (SAP Analytics Cloud)",
            "owner": "Dr. Anna Schneider (Compliance)",
            "classification": "high_risk_candidate",
            "lifecycle": "production",
            "readiness": "partially_covered",
            "risk": "high",
            "risk_likelihood": "likely",
            "nis2": True,
            "sector": "finance",
            "iso42001": True,
            "gap_families": ["A.7_Support"],
            "gap_severity": "minor",
            "gap_status": "remediation_planned",
        },
        {
            "system_id": "sap-demand-forecast-v1",
            "name": "Demand Forecasting",
            "description": "ML-gestützte Absatzplanung in SAP IBP",
            "owner": "Peter Wagner (Supply Chain)",
            "classification": "minimal",
            "lifecycle": "production",
            "readiness": "ready_for_review",
            "risk": "low",
            "risk_likelihood": "unlikely",
        },
    ],
    "sme_demo": [
        {
            "system_id": "support-chatbot-v1",
            "name": "Kunden-Support Chatbot",
            "description": "ChatGPT-basierter FAQ-Bot für Kundenanfragen",
            "owner": "Maria Hoffmann (Kundenservice)",
            "classification": "limited",
            "lifecycle": "production",
            "readiness": "unknown",
            "risk": "medium",
            "risk_likelihood": "possible",
        },
        {
            "system_id": "email-filter-v1",
            "name": "Spam-/Phishing-Filter",
            "description": "ML-basierte E-Mail-Filterung",
            "owner": "IT-Abteilung",
            "classification": "minimal",
            "lifecycle": "production",
            "readiness": "unknown",
            "risk": "low",
            "risk_likelihood": "unlikely",
        },
    ],
}
