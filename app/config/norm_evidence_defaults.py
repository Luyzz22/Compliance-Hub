"""Statische Default-Empfehlungen für Norm-Nachweise (beratergetrieben, nicht automatisch)."""

from __future__ import annotations

# Hinweis: Diese Defaults sind generisch (nicht tenant-spezifisch) und dienen als Vorschläge.
# Sie werden NICHT automatisch angelegt; nur als UI-/Berater-Assistenz.

DEFAULT_NORM_EVIDENCE_MAPPINGS: list[dict[str, str]] = [
    {
        "framework": "EU_AI_ACT",
        "reference": "Art. 9",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Nachweis für Risikomanagement und kontinuierliches "
            "Monitoring von High-Risk-KI-Systemen."
        ),
    },
    {
        "framework": "EU_AI_ACT",
        "reference": "Art. 17",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Nachweis für ein AI-Managementsystem (Governance, "
            "Kontrollen, Kennzahlen) – vorbereitet für ISO 42001."
        ),
    },
    {
        "framework": "EU_AI_ACT",
        "reference": "Art. 61",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Input für Post-Market-Monitoring: Trends, Incidents "
            "und Alerts als kontinuierliche Überwachung."
        ),
    },
    {
        "framework": "NIS2",
        "reference": "Art. 21",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Nachweis für Risikomanagementmaßnahmen, Incident-Readiness "
            "und Lieferanten-Risiko-Überblick gegenüber Leitungsorganen."
        ),
    },
    {
        "framework": "NIS2",
        "reference": "Art. 24",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Evidenz für Supply-Chain-Risiken "
            "(Supplier Coverage, kritische Lieferanten)."
        ),
    },
    {
        "framework": "ISO_42001",
        "reference": "6.2",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Evidenz für AI-Governance-Ziele, Messung und Managementbewertung."
        ),
    },
    {
        "framework": "ISO_42001",
        "reference": "8.1",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Evidenz für operative Steuerung: KPIs, Alerts "
            "und definierte Schwellenwerte."
        ),
    },
    {
        "framework": "ISO_42001",
        "reference": "9.1",
        "evidence_type": "board_report",
        "note": (
            "Board-Report als Evidenz für Monitoring, Measurement & Evaluation der AI-Governance."
        ),
    },
]
