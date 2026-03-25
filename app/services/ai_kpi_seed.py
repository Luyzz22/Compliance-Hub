"""Seed: Standard-KPIs/KRIs für High-Risk-KI (EU AI Act Monitoring, ISO 42001 Performance)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models_db import AiKpiDefinitionDB

_STANDARD_ROWS: list[dict[str, Any]] = [
    {
        "key": "incident_rate_ai",
        "name": "Incident-Rate (KI-bezogen)",
        "description": (
            "Anteil oder Anzahl sicherheits- oder compliance-relevanter Vorfälle pro Periode, "
            "die diesem KI-System zugeordnet sind (interne Taxonomie)."
        ),
        "category": "compliance",
        "unit": "percent",
        "recommended_direction": "down",
        "framework_tags": ["eu_ai_act", "nis2", "iso_42001"],
        "alert_threshold_high": 2.0,
        "alert_threshold_low": None,
    },
    {
        "key": "jailbreak_success_rate",
        "name": "Prompt-/Jailbreak-Erfolgsrate (Red Team)",
        "description": (
            "Anteil erfolgreicher Jailbreak- oder Policy-Umgehungsversuche in strukturierten "
            "Red-Team-Tests."
        ),
        "category": "security",
        "unit": "percent",
        "recommended_direction": "down",
        "framework_tags": ["eu_ai_act", "iso_42001"],
        "alert_threshold_high": 5.0,
        "alert_threshold_low": None,
    },
    {
        "key": "pii_leakage_rate",
        "name": "PII-Leakage-Rate / Datenschutzvorfälle",
        "description": (
            "Rate erkannter PII-Leaks oder datenschutzrelevanter Vorfälle je Periode "
            "(Tests, Monitoring, Meldungen)."
        ),
        "category": "privacy",
        "unit": "percent",
        "recommended_direction": "down",
        "framework_tags": ["dsgvo", "eu_ai_act", "iso_42001"],
        "alert_threshold_high": 0.5,
        "alert_threshold_low": None,
    },
    {
        "key": "drift_indicator",
        "name": "Modell-/Daten-Drift-Indikator",
        "description": (
            "Aggregierter Drift-Score oder qualitativer Index (0–100); höhere Werte = "
            "stärkere Abweichung vom Referenz-/Trainingsprofil."
        ),
        "category": "quality",
        "unit": "index",
        "recommended_direction": "down",
        "framework_tags": ["eu_ai_act", "iso_42001"],
        "alert_threshold_high": 35.0,
        "alert_threshold_low": None,
    },
    {
        "key": "false_negative_rate_safety",
        "name": "Safety-False-Negative-Rate",
        "description": (
            "Anteil sicherheitskritischer Outputs, die von Filtern/Guards nicht abgefangen wurden."
        ),
        "category": "safety",
        "unit": "percent",
        "recommended_direction": "down",
        "framework_tags": ["eu_ai_act", "iso_42001"],
        "alert_threshold_high": 1.0,
        "alert_threshold_low": None,
    },
    {
        "key": "human_oversight_bypass_rate",
        "name": "Human-Oversight-Bypass-Rate",
        "description": (
            "Anteil Fälle mit vorgesehener menschlicher Kontrolle, in denen Overrides, "
            "Ausnahmen oder Umgehungen ohne dokumentierte Freigabe erfolgten."
        ),
        "category": "compliance",
        "unit": "percent",
        "recommended_direction": "down",
        "framework_tags": ["eu_ai_act", "iso_42001"],
        "alert_threshold_high": 3.0,
        "alert_threshold_low": None,
    },
    {
        "key": "nis2_ai_security_incident_count",
        "name": "NIS2: KI-bezogene Security-Incidents",
        "description": (
            "Anzahl sicherheitsrelevanter Vorfälle mit Bezug zu diesem KI-System "
            "im Berichtszeitraum."
        ),
        "category": "security",
        "unit": "absolute",
        "recommended_direction": "down",
        "framework_tags": ["nis2", "iso_27001"],
        "alert_threshold_high": 1.0,
        "alert_threshold_low": None,
    },
    {
        "key": "performance_regression_index",
        "name": "Performance-Regressions-Index",
        "description": (
            "Zusammenfassender Index für Qualitäts- oder Latenz-Regression ggü. Baseline "
            "(höher = stärkere Regression)."
        ),
        "category": "quality",
        "unit": "index",
        "recommended_direction": "down",
        "framework_tags": ["iso_42001", "eu_ai_act"],
        "alert_threshold_high": 25.0,
        "alert_threshold_low": None,
    },
]


def ensure_ai_kpi_definitions_seeded(session: Session) -> None:
    """Idempotent: legt fehlende Standard-Definitionen an."""
    for row in _STANDARD_ROWS:
        key = row["key"]
        existing = session.execute(
            select(AiKpiDefinitionDB.id).where(AiKpiDefinitionDB.key == key),
        ).scalar_one_or_none()
        if existing is not None:
            continue
        session.add(
            AiKpiDefinitionDB(
                id=str(uuid.uuid4()),
                key=key,
                name=row["name"],
                description=row["description"],
                category=row["category"],
                unit=row["unit"],
                recommended_direction=row["recommended_direction"],
                framework_tags=list(row["framework_tags"]),
                alert_threshold_high=row["alert_threshold_high"],
                alert_threshold_low=row["alert_threshold_low"],
            ),
        )
    session.commit()
