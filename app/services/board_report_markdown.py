"""Markdown-Export für AI Board Governance Report (template-fähig, deterministisch)."""

from __future__ import annotations

from datetime import datetime

from app.ai_governance_models import (
    AIBoardGovernanceReport,
    BoardOperationalMonitoringSection,
    OamiIncidentSubtypeProfile,
)


def _fmt_pct(value: float) -> str:
    return f"{round(value * 100)} %"


def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y")


_BULLET_SAFETY_SUBTYPE_DE = (
    "Im Berichtszeitraum überwiegen bzw. sind anteilig stark sicherheitsrelevante "
    "Laufzeit-Incidents (z. B. sicherheitsbezogene Vorfälle im KI-Betrieb). "
    "Diese fließen im OAMI stärker in die Bewertung ein als reine Verfügbarkeitssignale."
)

_BULLET_AVAILABILITY_SUBTYPE_DE = (
    "Verfügbarkeits- und leistungsbezogene Signale (Betriebsstabilität, Metrik-Schwellen) "
    "machen den größeren Teil der sichtbaren Last aus bzw. dominieren das Laufzeitbild."
)

_BULLET_BALANCED_SUBTYPE_DE = (
    "Die sichtbare Incident-Last verteilt sich über mehrere Subtyp-Kategorien; es liegt "
    "keine einseitige Dominanz von Sicherheits- gegenüber Verfügbarkeitssignalen vor."
)


def _append_oami_subtype_markdown_block(
    lines: list[str],
    om: BoardOperationalMonitoringSection,
    profile: OamiIncidentSubtypeProfile,
) -> None:
    sh = profile.incident_weighted_share_safety
    av = profile.incident_weighted_share_availability
    ot = profile.incident_weighted_share_other
    safety_dom = sh >= 0.45 and sh > av and sh > ot
    avail_dom = av >= 0.45 and av > sh and av > ot

    lines.append("")
    lines.append("### Operatives AI-Monitoring – Incident-Subtypen")
    lines.append("")
    lines.append(
        "Einordnung der Laufzeit-Incidents für den OAMI – ohne Melde- oder Rechtsqualifikation.",
    )
    lines.append("")
    if safety_dom:
        lines.append(f"- {_BULLET_SAFETY_SUBTYPE_DE}")
    elif avail_dom:
        lines.append(f"- {_BULLET_AVAILABILITY_SUBTYPE_DE}")
    else:
        lines.append(f"- {_BULLET_BALANCED_SUBTYPE_DE}")

    if (profile.oami_subtype_narrative_de or "").strip():
        lines.append(f"- {profile.oami_subtype_narrative_de.strip()}")

    ps = round(sh * 100)
    pa = round(av * 100)
    po = round(ot * 100)
    lbl = profile.category_labels_de
    lines.append(
        f"- Verteilung (gewichteter Fokus, normiert): "
        f"{lbl.get('safety', 'Sicherheit')} ca. {ps} %, "
        f"{lbl.get('availability', 'Verfügbarkeit')} ca. {pa} %, "
        f"{lbl.get('other', 'Sonstige')} ca. {po} %.",
    )
    lines.append("")
    lines.append("<!-- chart:oami-subtype-shares -->")
    lines.append("")
    lines.append(f"*Hinweis Diagramm (Export):* {profile.chart_note_de}")
    lines.append("")


def render_board_report_markdown(report: AIBoardGovernanceReport) -> str:
    """
    Erzeugt ein strukturiertes Markdown-Dokument aus dem Board-Report.
    Deterministisch aus Zahlen, keine LLM-Aufrufe. Keine personenbezogenen Daten.
    """
    k = report.kpis
    c = report.compliance_overview
    i = report.incidents_overview
    s = report.supplier_risk_overview
    date_str = _fmt_date(report.generated_at)

    lines: list[str] = [
        f"# AI Governance Board Report – {report.tenant_id} ({date_str})",
        "",
        f"*Berichtszeitraum: {report.period}*",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
    ]

    # Kurze, deterministische Sätze aus KPIs/Alerts
    lines.append(f"- AI-Systeme gesamt: {k.ai_systems_total} (aktiv: {k.active_ai_systems}).")
    lines.append(
        f"- High-Risk-Systeme: {k.high_risk_systems}; "
        f"davon ohne DPIA: {k.high_risk_systems_without_dpia}."
    )
    lines.append(
        f"- ISO 42001 Governance-Score: {_fmt_pct(k.iso42001_governance_score)}; "
        f"NIS2 Incident Readiness: {_fmt_pct(k.nis2_incident_readiness_ratio)}; "
        f"Supplier Risk Coverage: {_fmt_pct(k.nis2_supplier_risk_coverage_ratio)}."
    )
    nis2_mean = (
        f"{round(c.nis2_kritis_kpi_mean_percent)} %"
        if c.nis2_kritis_kpi_mean_percent is not None
        else "k. A."
    )
    nis2_cov = f"{round(c.nis2_kritis_systems_full_coverage_ratio * 100)} %"
    lines.append(
        f"- EU AI Act / ISO 42001 Gesamt-Readiness: {_fmt_pct(c.overall_readiness)}; "
        f"Frist High-Risk: {c.days_remaining} Tage (bis {c.deadline})."
    )
    lines.append(
        f"- NIS2 / KRITIS KPI (persistente Kennzahlen): Mittelwert {nis2_mean}; "
        f"Vollständige Systemabdeckung (alle drei KPI-Typen): {nis2_cov}."
    )
    lines.append(
        f"- Offene Incidents (12 Monate): {i.total_incidents_last_12_months}; "
        f"offen: {i.open_incidents}."
    )
    lines.append(
        f"- Lieferanten-Risiko: {s.systems_without_supplier_risk_register} Systeme ohne "
        f"Supplier-Risikoregister (von {s.total_systems_with_suppliers} mit Lieferantenbezug)."
    )
    if report.alerts:
        critical = sum(1 for a in report.alerts if a.severity == "critical")
        lines.append(f"- **{len(report.alerts)} Alert(s)** (davon {critical} kritisch).")
    else:
        lines.append("- Keine aktuellen Alerts.")
    om = report.operational_monitoring
    if om is not None:
        lines.append("")
        lines.append(
            f"- **Operatives KI-Monitoring (OAMI, {om.window_days} Tage):** "
            f"{om.index_value}/100 ({om.level}), "
            f"{'Signale vorhanden' if om.has_data else 'keine Laufzeitdaten'} "
            f"({om.systems_scored} Systeme mit Daten)."
        )
        lines.append(f"  - Kurzfassung: {om.summary_de}")
        for d in om.drivers_de[:5]:
            lines.append(f"  - Treiber: {d}")
        prof = om.oami_incident_subtype_profile
        if prof is not None:
            _append_oami_subtype_markdown_block(lines, om, prof)
    lines.extend(["", "---", "", "## 2. KPIs", ""])

    # KPIs als Tabelle
    lines.extend(
        [
            "| Kennzahl | Wert |",
            "|----------|------|",
            f"| Board Maturity Score | {_fmt_pct(k.board_maturity_score)} |",
            f"| ISO 42001 Governance Score | {_fmt_pct(k.iso42001_governance_score)} |",
            f"| NIS2 Incident Readiness Ratio | {_fmt_pct(k.nis2_incident_readiness_ratio)} |",
            f"| NIS2 Supplier Risk Coverage | {_fmt_pct(k.nis2_supplier_risk_coverage_ratio)} |",
            f"| High-Risk-Systeme ohne DPIA | {k.high_risk_systems_without_dpia} |",
            f"| Kritische Systeme ohne Owner | {k.critical_systems_without_owner} |",
            f"| NIS2-Kontrolllücken (gesamt) | {k.nis2_control_gaps} |",
            "",
        ]
    )
    nis2_k_mean = (
        f"{round(k.nis2_kritis_kpi_mean_percent)} %"
        if k.nis2_kritis_kpi_mean_percent is not None
        else "k. A."
    )
    nis2_k_cov = f"{round(k.nis2_kritis_systems_full_coverage_ratio * 100)} %"
    lines.extend(
        [
            f"| NIS2 / KRITIS KPI Mittelwert (0–100) | {nis2_k_mean} |",
            f"| NIS2 / KRITIS KPI Systemabdeckung (alle 3 Typen) | {nis2_k_cov} |",
            "",
        ]
    )

    lines.extend(
        [
            "---",
            "",
            "## 3. Compliance-Readiness EU AI Act / ISO 42001",
            "",
            f"- **Gesamt-Readiness:** {_fmt_pct(c.overall_readiness)}",
            f"- High-Risk-Systeme voll kontrolliert: {c.high_risk_systems_with_full_controls}",
            f"- High-Risk-Systeme mit kritischen Lücken: {c.high_risk_systems_with_critical_gaps}",
            f"- Frist (High-Risk): {c.deadline} ({c.days_remaining} Tage verbleibend)",
            "",
        ]
    )
    if c.top_critical_requirements:
        lines.append("**Top kritische Anforderungen:**")
        for req in c.top_critical_requirements[:5]:
            lines.append(f"- {req.article}: {req.name} – {req.affected_systems_count} System(e)")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 4. Incidents",
            "",
            f"- Incidents (letzte 12 Monate): {i.total_incidents_last_12_months}",
            f"- Offene Incidents: {i.open_incidents}",
            f"- Schwerwiegende Incidents (12 Monate): {i.major_incidents_last_12_months}",
            "",
        ]
    )
    if i.mean_time_to_ack_hours is not None:
        lines.append(f"- Mittlere Zeit bis Bestätigung: {i.mean_time_to_ack_hours:.1f} h")
    if i.mean_time_to_recover_hours is not None:
        lines.append(f"- Mittlere Zeit bis Wiederherstellung: {i.mean_time_to_recover_hours:.1f} h")
    if i.by_severity:
        lines.append("Nach Schweregrad:")
        for e in i.by_severity:
            lines.append(f"- {e.severity}: {e.count}")
        lines.append("")
    else:
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 5. Supplier-Risiken",
            "",
            f"- Systeme mit Lieferantenbezug: {s.total_systems_with_suppliers}",
            f"- Davon ohne Supplier-Risikoregister: {s.systems_without_supplier_risk_register}",
            f"- Kritische Lieferanten gesamt: {s.critical_suppliers_total}",
            f"- Kritische Lieferanten ohne Kontrollen: {s.critical_suppliers_without_controls}",
            "",
        ]
    )
    if s.by_risk_level:
        lines.append("| Risikostufe | Mit Register | Ohne Register |")
        lines.append("|-------------|--------------|---------------|")
        for e in s.by_risk_level:
            row = f"| {e.risk_level} | {e.systems_with_register} | {e.systems_without_register} |"
            lines.append(row)
        lines.append("")
    lines.extend(["---", "", "## 6. Alerts & Maßnahmenempfehlungen", ""])

    if report.alerts:
        for a in report.alerts:
            lines.append(f"- **[{a.severity.upper()}]** {a.message}")
        lines.append("")
    else:
        lines.append("Keine offenen Alerts.")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 7. Ausblick (operatives Monitoring & nächste Schritte)",
            "",
        ],
    )
    if om is not None:
        if om.has_data:
            lines.append(
                "Die aggregierte Laufzeitlage stützt EU-AI-Act-Post-Market- und "
                "ISO-42001-Überwachungsnachweise; Priorität: wiederkehrende Signale und "
                "saubere Eskalation bei Incidents."
            )
        else:
            lines.append(
                "Ohne sichtbare Laufzeit-Signale sollten Anbindungen (z. B. SAP AI Core/BTP) "
                "oder definierte manuelle Meldewege priorisiert werden."
            )
        if om.drivers_de:
            lines.append("")
            lines.append("**Konkrete Hinweise aus dem OAMI:**")
            for d in om.drivers_de[:6]:
                lines.append(f"- {d}")
    else:
        lines.append(
            "Operatives Monitoring-Abschnitt nicht verfügbar; technische Auswertung prüfen."
        )
    lines.append("")

    return "\n".join(lines)
