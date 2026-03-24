"""Statische Default-Empfehlungen für Norm-Nachweise (EU AI Act / NIS2 / ISO 42001).

Beratergetrieben.
"""

from __future__ import annotations

from typing import List, Literal, NotRequired, TypedDict  # noqa: UP035

NormFramework = Literal["EU_AI_ACT", "NIS2", "ISO_42001"]
EvidenceType = Literal["board_report", "export_job", "other"]


class NormEvidenceDefault(TypedDict):
    framework: NormFramework
    reference: str
    evidence_type: EvidenceType
    note: str


class HighRiskScenarioProfileConfig(TypedDict):
    """Statisches High-Risk-AI-Szenario mit empfohlenen Norm-Nachweisen (keine DB-Anlage)."""

    id: str
    label: str
    description: str
    recommended_evidence: List[NormEvidenceDefault]  # noqa: UP006
    recommended_incident_response_maturity_percent: NotRequired[int | None]
    recommended_supplier_risk_coverage_percent: NotRequired[int | None]
    recommended_ot_it_segregation_percent: NotRequired[int | None]


DEFAULT_NORM_EVIDENCE_MAPPINGS: List[NormEvidenceDefault] = [  # noqa: UP006
    {
        "framework": "EU_AI_ACT",
        "reference": "Art. 9",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Nachweis für Risikomanagement und laufendes "
            "Monitoring von High-Risk-KI-Systemen."
        ),
    },
    {
        "framework": "EU_AI_ACT",
        "reference": "Art. 17",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Evidenz für das AI-Managementsystem nach ISO 42001 "
            "und dessen Aufsicht durch das Leitungsorgan."
        ),
    },
    {
        "framework": "NIS2",
        "reference": "Art. 21",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Nachweis für Risiko-Management, "
            "Sicherheitsmaßnahmen und Berichtspflichten gegenüber der Leitung."
        ),
    },
    {
        "framework": "ISO_42001",
        "reference": "6.2",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Evidenz für AI-Governance-Ziele und "
            "Managementbewertung gemäß ISO 42001."
        ),
    },
    {
        "framework": "ISO_42001",
        "reference": "8.1",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Evidenz für operative Steuerung, Kennzahlen "
            "und definierte Schwellwerte im AI-Managementsystem."
        ),
    },
    {
        "framework": "ISO_42001",
        "reference": "9.1",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Evidenz für Monitoring, Measurement, Analysis "
            "und Evaluation der AI-Governance."
        ),
    },
]

HIGH_RISK_SCENARIO_PROFILES: list[HighRiskScenarioProfileConfig] = [
    {
        "id": "manufacturing_quality_control",
        "label": "Qualitätskontrolle (High-Risk AI im produzierenden Gewerbe)",
        "description": (
            "Visuelle oder automatisierte Qualitätsprüfung sicherheitsrelevanter "
            "Komponenten; Fehlklassifikation kann Personen- oder Anlagenschäden "
            "verursachen."
        ),
        "recommended_evidence": [
            {
                "framework": "EU_AI_ACT",
                "reference": "Art. 9",
                "evidence_type": "board_report",
                "note": (
                    "Risikomanagement und laufendes Monitoring für High-Risk-KI in "
                    "der Fertigungs-QS."
                ),
            },
            {
                "framework": "NIS2",
                "reference": "Art. 21",
                "evidence_type": "board_report",
                "note": (
                    "Risikomanagement, operative Sicherheitsmaßnahmen und "
                    "Berichtslinie zur Leitung für OT/IT in der Produktion."
                ),
            },
            {
                "framework": "ISO_42001",
                "reference": "6.2",
                "evidence_type": "board_report",
                "note": (
                    "AI-Ziele und Kenngrößen für die QS-KI (Schwellen, "
                    "Fehlerquoten, Eskalation)."
                ),
            },
            {
                "framework": "ISO_42001",
                "reference": "8.1",
                "evidence_type": "board_report",
                "note": (
                    "Operative Steuerung der QS-Pipeline inkl. "
                    "Daten- und Modellüberwachung."
                ),
            },
            {
                "framework": "ISO_42001",
                "reference": "9.1",
                "evidence_type": "board_report",
                "note": (
                    "Monitoring, Messung und Bewertung der KI-QS (Audit, "
                    "Management Review)."
                ),
            },
        ],
        "recommended_incident_response_maturity_percent": 88,
        "recommended_supplier_risk_coverage_percent": 82,
        "recommended_ot_it_segregation_percent": 85,
    },
    {
        "id": "critical_infrastructure_predictive_maintenance",
        "label": "Predictive Maintenance (kritische Infrastruktur)",
        "description": (
            "Zustandsüberwachung und Prognosen für kritische Anlagen; Fehlprognosen "
            "können Ausfälle oder Gefährdungen der Versorgung begünstigen."
        ),
        "recommended_evidence": [
            {
                "framework": "EU_AI_ACT",
                "reference": "Anhang III Nr. 1",
                "evidence_type": "board_report",
                "note": (
                    "High-Risk-Einordnung Kritischer Infrastrukturen / "
                    "sicherheitsrelevante Anlagen (Anhang III)."
                ),
            },
            {
                "framework": "NIS2",
                "reference": "Art. 21",
                "evidence_type": "board_report",
                "note": (
                    "Risikomanagement und Cybersicherheitsmaßnahmen für OT-Monitoring "
                    "und Fernzugriff."
                ),
            },
            {
                "framework": "ISO_42001",
                "reference": "4.1",
                "evidence_type": "board_report",
                "note": (
                    "Kontext des AI-Managementsystems inkl. regulatorischer und "
                    "betrieblicher Anforderungen (KRITIS/NIS2)."
                ),
            },
            {
                "framework": "ISO_42001",
                "reference": "6.1",
                "evidence_type": "board_report",
                "note": (
                    "Maßnahmenplanung und Ressourcen für PM-KI (Alarmierung, "
                    "Eskalation, Wartung)."
                ),
            },
            {
                "framework": "ISO_42001",
                "reference": "9.1",
                "evidence_type": "board_report",
                "note": (
                    "Leistungsüberwachung der KI-Prognosen (Drift, "
                    "Fehlalarmquote, Verfügbarkeit)."
                ),
            },
        ],
        "recommended_incident_response_maturity_percent": 95,
        "recommended_supplier_risk_coverage_percent": 90,
        "recommended_ot_it_segregation_percent": 98,
    },
    {
        "id": "clinical_decision_support",
        "label": "Klinische Entscheidungsunterstützung (Healthcare)",
        "description": (
            "KI-gestützte Diagnose- oder Therapieempfehlungen; Fehlentscheidungen "
            "können Patientensicherheit und regulatorische Anforderungen (MPDG) berühren."
        ),
        "recommended_evidence": [
            {
                "framework": "EU_AI_ACT",
                "reference": "Art. 9",
                "evidence_type": "board_report",
                "note": "Risikomanagement und klinische Validierung für High-Risk-KI.",
            },
            {
                "framework": "NIS2",
                "reference": "Art. 21",
                "evidence_type": "board_report",
                "note": "Incident-Response und Business Continuity im Gesundheitswesen.",
            },
            {
                "framework": "ISO_42001",
                "reference": "6.1",
                "evidence_type": "board_report",
                "note": "AI-Risiken im klinischen Kontext.",
            },
        ],
        "recommended_incident_response_maturity_percent": 92,
        "recommended_supplier_risk_coverage_percent": 88,
        "recommended_ot_it_segregation_percent": 80,
    },
    {
        "id": "biometric_identification_high_risk",
        "label": "Biometrische Identifikation (hohes Risiko)",
        "description": (
            "Echtzeit- oder Fernidentifikation natürlicher Personen; hohe Anforderungen "
            "an Datenschutz, Sicherheit und Lieferkettenkontrolle."
        ),
        "recommended_evidence": [
            {
                "framework": "EU_AI_ACT",
                "reference": "Anhang III Nr. 1",
                "evidence_type": "board_report",
                "note": "High-Risk-Biometrie: Konformitätsbewertung und Monitoring.",
            },
            {
                "framework": "NIS2",
                "reference": "Art. 21",
                "evidence_type": "board_report",
                "note": "Sicherheitsmaßnahmen und Meldewege bei sicherheitsrelevanten Vorfällen.",
            },
        ],
        "recommended_incident_response_maturity_percent": 90,
        "recommended_supplier_risk_coverage_percent": 85,
        "recommended_ot_it_segregation_percent": 88,
    },
    {
        "id": "hr_recruitment_screening",
        "label": "HR / Recruiting (Screening)",
        "description": (
            "Automatisierte Bewerberauswahl oder -bewertung; Risiko für Diskriminierung "
            "und Arbeitsrecht; typischerweise geringere OT/IT-Trennung als in KRITIS."
        ),
        "recommended_evidence": [
            {
                "framework": "EU_AI_ACT",
                "reference": "Anhang III Nr. 4",
                "evidence_type": "board_report",
                "note": "High-Risk im Beschäftigungskontext.",
            },
            {
                "framework": "ISO_42001",
                "reference": "6.2",
                "evidence_type": "board_report",
                "note": "AI-Ziele und Fairness-Kenngrößen im HR-Kontext.",
            },
        ],
        "recommended_incident_response_maturity_percent": 72,
        "recommended_supplier_risk_coverage_percent": 68,
        "recommended_ot_it_segregation_percent": 55,
    },
]
