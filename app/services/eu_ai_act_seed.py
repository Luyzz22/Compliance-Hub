"""Seed-Daten: Beispiel-Tenant mit 2–3 KI-Systemen für Demo/Test (EU AI Act)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models_db import AISystemTable, RiskClassificationDB, TenantDB

logger = logging.getLogger(__name__)

SEED_TENANT_ID = "eu-ai-act-demo-tenant"
SEED_TENANT_NAME = "EU AI Act Demo GmbH"


def _tenant_exists(session: Session, tenant_id: str) -> bool:
    return session.get(TenantDB, tenant_id) is not None


def _system_exists(session: Session, system_id: str) -> bool:
    return session.get(AISystemTable, system_id) is not None


def seed_eu_ai_act_demo(session: Session) -> dict[str, int]:
    """Idempotent: legt Tenant + 3 KI-Systeme an, wenn nicht vorhanden."""
    created_systems = 0
    created_tenant = 0

    if not _tenant_exists(session, SEED_TENANT_ID):
        session.add(
            TenantDB(
                id=SEED_TENANT_ID,
                display_name=SEED_TENANT_NAME,
                industry="financial_services",
                country="DE",
                nis2_scope="in_scope",
                ai_act_scope="in_scope",
                is_demo=True,
                demo_playground=True,
            )
        )
        created_tenant = 1

    systems = [
        {
            "id": "demo-credit-scoring-v1",
            "name": "Credit Scoring AI",
            "description": (
                "KI-basiertes Kreditscoring für Privatkunden. "
                "Hochrisiko gemäß Anhang III Kategorie 5 (essential_services)."
            ),
            "business_unit": "Retail Banking",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "risk-team@demo.example.com",
            "criticality": "very_high",
            "data_sensitivity": "confidential",
            "has_incident_runbook": True,
            "has_supplier_risk_register": True,
            "has_backup_runbook": True,
            "intended_purpose": (
                "Automatisierte Kreditwürdigkeitsprüfung für Privatkredite "
                "bis 50.000 EUR auf Basis von Einkommensdaten und Zahlungshistorie."
            ),
            "training_data_provenance": (
                "Anonymisierte Kundendaten (2019-2024), SCHUFA-Score-Korrelation, "
                "Quelle: interne DWH-Exporte, bereinigt gemäß Art. 10 EU AI Act."
            ),
            "fria_reference": "FRIA-2025-CS-001 / DSFA-2025-007",
            "provider_name": "FinTech AI Solutions GmbH",
            "deployer_name": "EU AI Act Demo GmbH",
            "provider_responsibilities": (
                "Modellentwicklung, Validierung, technische Dokumentation, "
                "Konformitätsbewertung, Post-Market-Surveillance."
            ),
            "deployer_responsibilities": (
                "Betrieb gemäß Gebrauchsanweisung, menschliche Aufsicht (Art. 14), "
                "Logging und Incident-Meldung."
            ),
            "pms_status": "scheduled",
            "pms_next_review_date": (datetime.utcnow() + timedelta(days=90)).isoformat(),
            "classification": {
                "risk_level": "high_risk",
                "classification_path": "annex_iii",
                "annex_iii_category": 5,
                "profiles_natural_persons": True,
                "confidence_score": 1.0,
                "classified_by": "seed",
                "classification_rationale": (
                    "Hochrisiko via Anhang III Kategorie 5 (essential_services): "
                    "Kreditscoring mit Profiling natürlicher Personen."
                ),
            },
        },
        {
            "id": "demo-hr-cv-screening-v1",
            "name": "HR CV Screening AI",
            "description": (
                "Automatisches CV-Screening für Bewerber:innen. "
                "Hochrisiko gemäß Anhang III Kategorie 4 (employment)."
            ),
            "business_unit": "Human Resources",
            "risk_level": "high",
            "ai_act_category": "high_risk",
            "gdpr_dpia_required": True,
            "owner_email": "hr-tech@demo.example.com",
            "criticality": "high",
            "data_sensitivity": "restricted",
            "has_incident_runbook": False,
            "has_supplier_risk_register": False,
            "has_backup_runbook": False,
            "intended_purpose": (
                "Vorauswahl von Bewerber:innen auf Basis von Lebenslauf-Analyse "
                "und Kompetenz-Matching."
            ),
            "training_data_provenance": (
                "Anonymisierte Bewerbungsunterlagen (2020-2024), "
                "Quelle: internes ATS, bereinigt um geschützte Merkmale."
            ),
            "fria_reference": "FRIA-2025-HR-002",
            "provider_name": "TalentAI Europe B.V.",
            "deployer_name": "EU AI Act Demo GmbH",
            "provider_responsibilities": (
                "Modelltraining, Bias-Monitoring, technische Dokumentation."
            ),
            "deployer_responsibilities": (
                "Endauswahl durch menschlichen Recruiter, Art. 14 Aufsicht, Logging."
            ),
            "pms_status": "pending",
            "pms_next_review_date": None,
            "classification": {
                "risk_level": "high_risk",
                "classification_path": "annex_iii",
                "annex_iii_category": 4,
                "profiles_natural_persons": True,
                "confidence_score": 1.0,
                "classified_by": "seed",
                "classification_rationale": (
                    "Hochrisiko via Anhang III Kategorie 4 (employment): "
                    "CV-Screening betrifft Beschäftigung und Profiling."
                ),
            },
        },
        {
            "id": "demo-chatbot-support-v1",
            "name": "Customer Support Chatbot",
            "description": (
                "Konversations-KI für allgemeine Kundenanfragen. "
                "Begrenztes Risiko mit Transparenzpflichten (Art. 50)."
            ),
            "business_unit": "Customer Service",
            "risk_level": "limited",
            "ai_act_category": "limited_risk",
            "gdpr_dpia_required": False,
            "owner_email": "service@demo.example.com",
            "criticality": "medium",
            "data_sensitivity": "internal",
            "has_incident_runbook": True,
            "has_supplier_risk_register": False,
            "has_backup_runbook": True,
            "intended_purpose": (
                "Beantwortung allgemeiner Kundenanfragen zu Produkten und Services."
            ),
            "training_data_provenance": "FAQ-Datenbank und Produktdokumentation (kein PII).",
            "fria_reference": None,
            "provider_name": "EU AI Act Demo GmbH",
            "deployer_name": "EU AI Act Demo GmbH",
            "provider_responsibilities": (
                "Modellpflege, Inhaltskuratierung, Transparenzkennzeichnung."
            ),
            "deployer_responsibilities": "Transparenzhinweis an Nutzer (Art. 50).",
            "pms_status": "completed",
            "pms_next_review_date": (datetime.utcnow() + timedelta(days=180)).isoformat(),
            "pms_last_review_date": (datetime.utcnow() - timedelta(days=30)).isoformat(),
            "classification": {
                "risk_level": "limited_risk",
                "classification_path": "transparency",
                "annex_iii_category": None,
                "profiles_natural_persons": False,
                "confidence_score": 1.0,
                "classified_by": "seed",
                "classification_rationale": (
                    "Begrenztes Risiko: Chatbot/Konversations-KI mit Transparenzpflichten."
                ),
            },
        },
    ]

    for spec in systems:
        sid = spec["id"]
        if _system_exists(session, sid):
            continue

        cls_spec = spec.pop("classification")
        pms_next = spec.pop("pms_next_review_date")
        pms_last = spec.pop("pms_last_review_date", None)

        sys_row = AISystemTable(
            **spec,
            tenant_id=SEED_TENANT_ID,
            status="active",
            pms_next_review_date=(
                datetime.fromisoformat(pms_next) if isinstance(pms_next, str) else pms_next
            ),
            pms_last_review_date=(
                datetime.fromisoformat(pms_last) if isinstance(pms_last, str) else pms_last
            ),
        )
        session.add(sys_row)

        session.add(
            RiskClassificationDB(
                ai_system_id=sid,
                risk_level=cls_spec["risk_level"],
                classification_path=cls_spec["classification_path"],
                annex_iii_category=cls_spec["annex_iii_category"],
                profiles_natural_persons=cls_spec["profiles_natural_persons"],
                confidence_score=cls_spec["confidence_score"],
                classified_by=cls_spec["classified_by"],
                classification_rationale=cls_spec["classification_rationale"],
            )
        )
        created_systems += 1

    session.commit()
    if created_tenant or created_systems:
        logger.info(
            "EU AI Act seed: tenant=%d, systems=%d",
            created_tenant,
            created_systems,
        )
    return {"created_tenant": created_tenant, "created_systems": created_systems}
