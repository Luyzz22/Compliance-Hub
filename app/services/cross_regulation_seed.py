"""Idempotenter Seed: Regelwerks-Katalog, Crosswalks (keine Mandanten-Controls)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models_db import (
    ComplianceFrameworkDB,
    ComplianceRequirementDB,
    ComplianceRequirementRelationDB,
)


def _has_catalog(session: Session) -> bool:
    n = session.scalar(select(func.count()).select_from(ComplianceFrameworkDB))
    return bool(n and int(n) > 0)


def ensure_cross_regulation_catalog_seeded(session: Session) -> None:
    """Legt Frameworks, Requirements und Crosswalks an, falls noch leer."""
    if _has_catalog(session):
        return

    frameworks: list[tuple[str, str, str]] = [
        (
            "eu_ai_act",
            "EU AI Act",
            "High-Risk-KI, GPAI und Pflichten nach Verordnung (EU) 2024/1689.",
        ),
        ("iso_42001", "ISO/IEC 42001", "AI-Managementsystem (AIMS) – Governance und Lebenszyklus."),
        ("iso_27001", "ISO/IEC 27001", "Informationssicherheits-Managementsystem (ISMS)."),
        ("iso_27701", "ISO/IEC 27701", "Erweiterung ISO 27001 für Privacy Information Management."),
        (
            "nis2",
            "NIS2 / KRITIS",
            "Netzwerk- und Informationssicherheit (Richtlinie (EU) 2022/2555).",
        ),
        ("dsgvo", "DSGVO", "Datenschutz-Grundverordnung – Verarbeitung personenbezogener Daten."),
    ]
    fw_rows: dict[str, ComplianceFrameworkDB] = {}
    for key, name, desc in frameworks:
        row = ComplianceFrameworkDB(key=key, name=name, description=desc)
        session.add(row)
        fw_rows[key] = row
    session.flush()

    def fid(k: str) -> int:
        return int(fw_rows[k].id)

    reqs: list[tuple[str, str, str, str | None, str, str]] = [
        # (framework_key, code, title, description, type, criticality)
        ("eu_ai_act", "Art.9", "Risikomanagementsystem", None, "governance", "high"),
        ("eu_ai_act", "Art.10", "Datengovernance und Datenhaltung", None, "governance", "high"),
        ("eu_ai_act", "Art.11", "Technische Dokumentation", None, "documentation", "high"),
        ("eu_ai_act", "Art.12", "Protokollierung (Logging)", None, "technical", "high"),
        (
            "eu_ai_act",
            "Art.13",
            "Transparenz und Information der Nutzer",
            None,
            "process",
            "medium",
        ),
        ("eu_ai_act", "Art.14", "Menschliche Aufsicht", None, "process", "high"),
        (
            "eu_ai_act",
            "Art.15",
            "Genauigkeit, Robustheit und Cybersicherheit",
            None,
            "technical",
            "high",
        ),
        (
            "iso_42001",
            "4.1",
            "Kontext der Organisation (AIMS)",
            "Verständnis des Umfelds inkl. KI-spezifischer Themen.",
            "governance",
            "medium",
        ),
        (
            "iso_42001",
            "6.1",
            "Risiken und Chancen im AIMS adressieren",
            "Planung und Bewertung KI-bezogener Risiken.",
            "governance",
            "high",
        ),
        (
            "iso_42001",
            "8.2",
            "Daten für KI-Systeme",
            "Lebenszyklus von Daten für ML/KI.",
            "governance",
            "high",
        ),
        (
            "iso_42001",
            "9.1",
            "Überwachung, Messung und Bewertung",
            "Leistung des AIMS und KI-Systeme.",
            "process",
            "medium",
        ),
        ("iso_27001", "A.5", "Informationssicherheitsrichtlinien", None, "governance", "high"),
        ("iso_27001", "A.8", "Asset-Management", None, "governance", "medium"),
        ("iso_27001", "A.12", "Betrieb der Informationssicherheit", None, "technical", "high"),
        (
            "iso_27001",
            "A.16",
            "Management von Informationssicherheitsvorfällen",
            None,
            "process",
            "high",
        ),
        (
            "iso_27701",
            "PII-6.1",
            "Privacy-Risikomanagement (ISO 27701)",
            "Risiken für personenbezogene Daten.",
            "governance",
            "high",
        ),
        (
            "nis2",
            "Art.21(2)(b)",
            "Risikoanalyse und Sicherheitsmaßnahmen",
            None,
            "governance",
            "high",
        ),
        (
            "nis2",
            "Supply-Chain",
            "Lieferketten- und Dienstleister-Sicherheit",
            None,
            "governance",
            "high",
        ),
        ("nis2", "Art.23", "Meldung von Cyber-Sicherheitsvorfällen", None, "process", "high"),
        (
            "dsgvo",
            "Art.30",
            "Verzeichnis von Verarbeitungstätigkeiten (VVT)",
            None,
            "documentation",
            "medium",
        ),
        (
            "dsgvo",
            "Art.32",
            "Technische und organisatorische Maßnahmen (TOMs)",
            None,
            "technical",
            "high",
        ),
        ("dsgvo", "Art.35", "Datenschutz-Folgenabschätzung (DPIA)", None, "process", "high"),
    ]

    code_index: dict[tuple[str, str], int] = {}
    for fw_key, code, title, desc, rtype, crit in reqs:
        r = ComplianceRequirementDB(
            framework_id=fid(fw_key),
            code=code,
            title=title,
            description=desc,
            requirement_type=rtype,
            criticality=crit,
        )
        session.add(r)
        session.flush()
        code_index[(fw_key, code)] = int(r.id)

    def rid(fw: str, code: str) -> int:
        return code_index[(fw, code)]

    pairs: list[tuple[str, str, str, str, str | None]] = [
        ("eu_ai_act", "Art.9", "iso_42001", "6.1", "Risiko / AIMS"),
        ("eu_ai_act", "Art.9", "iso_27001", "A.5", "Policies & Governance"),
        ("eu_ai_act", "Art.9", "iso_27001", "A.8", "Asset / Datenbezug"),
        ("eu_ai_act", "Art.9", "nis2", "Art.21(2)(b)", "NIS2 Risikomanagement"),
        ("eu_ai_act", "Art.10", "iso_42001", "8.2", "Daten für KI"),
        ("eu_ai_act", "Art.10", "iso_27001", "A.8", "Asset-Management"),
        ("eu_ai_act", "Art.11", "iso_42001", "9.1", "Überwachung & Dokumentation"),
        ("eu_ai_act", "Art.11", "iso_27001", "A.12", "Betrieb / technische Maßnahmen"),
        ("eu_ai_act", "Art.12", "iso_27001", "A.12", "Logging / Betrieb"),
        ("eu_ai_act", "Art.12", "iso_27001", "A.16", "Vorfälle"),
        ("eu_ai_act", "Art.12", "nis2", "Art.23", "Incident-Meldung"),
        ("dsgvo", "Art.35", "eu_ai_act", "Art.9", "DPIA ↔ KI-Risiko"),
        ("dsgvo", "Art.35", "iso_27701", "PII-6.1", "Privacy-Risiko"),
        ("eu_ai_act", "Art.15", "iso_27001", "A.12", "Cybersicherheit / Betrieb"),
    ]

    seen: set[tuple[int, int]] = set()
    for f1, c1, f2, c2, note in pairs:
        a, b = rid(f1, c1), rid(f2, c2)
        lo, hi = (a, b) if a < b else (b, a)
        if (lo, hi) in seen:
            continue
        seen.add((lo, hi))
        session.add(
            ComplianceRequirementRelationDB(
                source_requirement_id=lo,
                target_requirement_id=hi,
                note=note,
            )
        )

    session.commit()
