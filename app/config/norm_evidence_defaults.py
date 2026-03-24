"""Statische Default-Empfehlungen für Norm-Nachweise (EU AI Act / NIS2 / ISO 42001).

Beratergetrieben.
"""

from __future__ import annotations

from typing import List, Literal, TypedDict  # noqa: UP035

NormFramework = Literal["EU_AI_ACT", "NIS2", "ISO_42001"]
EvidenceType = Literal["board_report", "export_job", "other"]


class NormEvidenceDefault(TypedDict):
    framework: NormFramework
    reference: str
    evidence_type: EvidenceType
    note: str


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
