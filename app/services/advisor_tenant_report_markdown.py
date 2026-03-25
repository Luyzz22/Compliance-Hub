from __future__ import annotations

from app.advisor_models import AdvisorTenantReport


def render_tenant_report_markdown(report: AdvisorTenantReport) -> str:
    """Kompakter Markdown-Steckbrief für PDF/Slides/Executive-Summary."""
    loc = " / ".join(x for x in (report.industry, report.country) if x) or "–"
    top_lines = "\n".join(
        f"- **{r.code}** – {r.name} (betroffene Systeme: {r.affected_systems_count})"
        for r in report.top_critical_requirements
    ) or "- Keine priorisierten Lücken in der aktuellen Readiness-Heuristik."

    open_setup = "\n".join(f"- {s}" for s in report.setup_open_step_labels) or "- Alle Setup-Schritte erfüllt."

    ot_it = (
        f"{report.nis2_ot_it_segregation_mean_percent:.0f}%"
        if report.nis2_ot_it_segregation_mean_percent is not None
        else "k. A. (keine KPI-Werte)"
    )

    return f"""# Compliance Hub Mandanten-Steckbrief – {report.tenant_name}

**Mandanten-ID:** `{report.tenant_id}`  
**Stand (UTC):** {report.generated_at_utc.isoformat()}

## Profil

- Branche / Region: {loc}
- KI-Systeme gesamt: **{report.ai_systems_total}**
- High-Risk-Systeme (Register): **{report.high_risk_systems_count}**
- High-Risk mit vollständigen Essential-Controls: **{report.high_risk_with_full_controls_count}**

## EU AI Act

- Readiness-Score: **{round(report.eu_ai_act_readiness_score * 100)}%**
- Stichtag: **{report.eu_ai_act_deadline}** ({report.eu_ai_act_days_remaining} Tage verbleibend)
- Top-Lücken (Auszug):
{top_lines}

## NIS2 / KRITIS

- Incident Readiness (Anteil Systeme mit Incident- und Backup-Runbook): **{report.nis2_incident_readiness_percent:.0f}%**
- Supplier Risk Coverage (Anteil mit Lieferanten-Register): **{report.nis2_supplier_risk_coverage_percent:.0f}%**
- OT/IT-Segregation (Mittel aus KPI-Tabelle): **{ot_it}**
- Kritische Fokus-Systeme (OT/IT-KPI unter Schwelle): **{report.nis2_critical_focus_systems_count}**

## Governance und Maßnahmen

- Offene Actions (open / in progress): **{report.governance_open_actions_count}**
- Überfällige Actions (mit Fälligkeit): **{report.governance_overdue_actions_count}**
- Guided Setup: **{report.setup_completed_steps}/{report.setup_total_steps}** Schritte abgeschlossen
- Noch offene Setup-Schritte:
{open_setup}

---
*Compliance Hub – Kurzreport für Angebot, Kickoff oder Vorstand. Daten aus Register, Readiness und KPIs.*
"""
