"""LLM: Markdown-Board-Report aus strukturiertem Input (Claude-first, Legal-Reasoning-Pfad)."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.ai_compliance_board_report_models import AiComplianceBoardReportInput
from app.llm_models import LLMTaskType
from app.services.llm_router import LLMRouter

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

AI_COMPLIANCE_BOARD_REPORT_SYSTEM_DE = (
    "Du bist ein erfahrener GRC- und AI-Governance-Berater für den deutschsprachigen Raum "
    "(DE/AT/CH), spezialisiert auf EU AI Act, ISO 42001, ISO 27001/27701, NIS2/KRITIS-Dachgesetz "
    "und DSGVO. Erstelle knappe, verständliche Board- und Management-Reports. Fokus: Risiken, "
    "Coverage, Handlungsprioritäten. Schreibe deutsch, ohne Marketing-Sprache, mit klaren "
    "Überschriften und Bullet Points. Keine Vollzitate von Normtexten, nur Kurzreferenzen "
    "(z. B. „EU AI Act Art. 9 – Risikomanagementsystem“). Maximal etwa zwei Seiten Fließtext "
    "Umfang (bei Export als PDF)."
)


def _audience_label(audience: str) -> str:
    return {
        "board": "Vorstand/Aufsicht",
        "management": "Geschäftsführung/Management",
        "advisor_client": "Berater-Mandantenbericht",
    }.get(audience, audience)


def build_board_report_user_prompt(inp: AiComplianceBoardReportInput) -> str:
    payload = inp.model_dump()
    gov_block = ""
    para_de = (inp.governance_maturity_executive_paragraph_de or "").strip()
    if para_de:
        quoted = para_de
        gov_block = (
            "\n**Governance-Reife (Pflicht):** Unter „## Executive Overview“ beginne mit "
            "**genau einem** Absatz, der **wörtlich** dem folgenden Text entspricht "
            "(keine Änderung, kein Zusammenfassen):\n\n"
            f'"""\n{quoted}\n"""\n\n'
            "Optional **ein** weiterer kurzer Absatz (höchstens 3 Sätze) zur Einordnung der "
            "übrigen Report-Daten — ohne die Governance-Kernaussage zu wiederholen.\n"
        )
    status_gov = ""
    if inp.governance_maturity_summary is not None:
        status_gov = (
            "\n**Status — Governance-Reife:** Im Abschnitt „## Status & Kennzahlen“ füge nach der "
            "Framework-Coverage einen Unterblock **Governance-Reife (Readiness, GAI, OAMI)** ein: "
            "je ein knapper Satz Interpretation pro Säule, basierend auf dem JSON-Feld "
            "`governance_maturity_summary` "
            "(Felder `short_reason` / `overall_assessment.short_summary`). "
            "Wiederhole **keine** numerischen Scores oder Indizes aus dem JSON "
            "(Frontend zeigt Zahlen); keine deutschen UI-Stufenbezeichnungen aus dem Contract "
            "ausformulieren.\n"
            "Im Abschnitt „## Ausblick & nächste Meilensteine“ nimm **optional** 1–2 Sätze auf, "
            "die sich aus `overall_assessment.key_risks` und `key_strengths` ableiten "
            "(priorisiert, ohne neue Fakten).\n"
        )
    exec_intro = "" if gov_block else "1–2 knappe Absätze.\n"
    structure = (
        "Erzeuge ein Markdown-Dokument mit exakt diesen Hauptüberschriften (##):\n"
        "## Executive Overview\n"
        f"{exec_intro}{gov_block}"
        "## Regulatorischer Scope\n"
        "Welche Frameworks sind aus den Daten erkennbar im Scope "
        "(EU AI Act, NIS2, ISO 42001/27001, DSGVO etc.).\n"
        "## Status & Kennzahlen\n"
        "Coverage-Übersicht pro Framework, relevante KI-Inventar-Kennzahlen aus dem JSON.\n"
        f"{status_gov}"
        "## AI Performance & Risk KPIs\n"
        "Nutze high_risk_kpi_summaries und kpi_portfolio_aggregates aus dem JSON (falls leer: "
        "kurz vermerken, dass noch keine KPI-Zeitreihen gepflegt werden). "
        "Interpretation sachlich und trendorientiert, ohne Alarmismus; "
        "Prioritäten aus auffälligen Metriken ableiten. "
        "Kurz den Normenkontext erwähnen: EU AI Act (Monitoring und Dokumentation der "
        "Systemleistung im Betrieb) sowie ISO 42001 (Performance Evaluation des "
        "AI-Managementsystems). Keine Personenbezüge, nur Systemkennzahlen.\n"
        "## Wesentliche Gaps & Risiken\n"
        "Die wichtigsten 5–10 Lücken mit Kurzreferenz (kein Vollzitat).\n"
        "## Empfohlene Maßnahmen (nächste 90 Tage)\n"
        "Priorisierte Bullet-Liste mit Rollen (CISO, AI Owner, GF …), nutze gap_assist_hints falls "
        "vorhanden.\n"
        "## Ausblick & nächste Meilensteine\n"
        "z. B. EU AI Act / NIS2 Fristen allgemein, Audit-/Review-Hinweise – ohne konkrete "
        "Rechtsberatung.\n\n"
        f"Zielgruppe: {_audience_label(inp.audience_type)}.\n"
        "Antwort nur als Markdown, ohne einleitenden Fließtext vor der ersten ##-Überschrift.\n\n"
        f"Eingabe-JSON (nur Metadaten):\n{json.dumps(payload, ensure_ascii=False)}"
    )
    return structure


def render_ai_compliance_board_report_markdown(
    inp: AiComplianceBoardReportInput,
    tenant_id: str,
    *,
    session: Session | None,
) -> str:
    user = build_board_report_user_prompt(inp)
    full_prompt = f"{AI_COMPLIANCE_BOARD_REPORT_SYSTEM_DE}\n\n{user}"
    router = LLMRouter(session=session)
    resp = router.route_and_call(LLMTaskType.AI_COMPLIANCE_BOARD_REPORT, full_prompt, tenant_id)
    text = (resp.text or "").strip()
    if not text:
        logger.warning("empty_board_report_llm_output tenant=%s", tenant_id)
    return text
