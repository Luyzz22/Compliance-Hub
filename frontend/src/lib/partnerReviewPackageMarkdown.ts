/**
 * Wave 44 – Markdown für Partner-Review-Paket (deutsch, partnerfreundlich).
 */

import { GTM_READINESS_LABELS_DE } from "@/lib/gtmAccountReadiness";
import type { PartnerReviewPackageDto } from "@/lib/partnerReviewPackageTypes";

function lineLabel(row: { mandant_label: string | null; tenant_id: string }): string {
  return row.mandant_label ? `${row.mandant_label} (${row.tenant_id})` : row.tenant_id;
}

export function partnerReviewPackageMarkdownDe(pkg: PartnerReviewPackageDto): string {
  const a = pkg.part_a_portfolio_overview;
  const m = pkg.meta;
  const lines: string[] = [];

  lines.push("# Kanzlei Partner-Review-Paket");
  lines.push("");
  lines.push(
    `Erzeugt: ${new Date(m.generated_at).toLocaleString("de-DE")} · Portfolio-Stand: ${new Date(m.portfolio_generated_at).toLocaleString("de-DE")}`,
  );
  lines.push(
    `Vergleich mit Baseline: ${m.compared_to_baseline ? "ja" : "nein"}${m.baseline_period_label ? ` (${m.baseline_period_label})` : ""}`,
  );
  lines.push("");

  lines.push("## A) Portfolio-Überblick");
  lines.push("");
  lines.push(`- Mandanten gesamt: **${a.total_mandanten}**`);
  lines.push(`- Backend erreichbar: ${a.backend_reachable ? "ja" : "nein"}`);
  if (a.tenants_partial_api > 0) {
    lines.push(`- API teilweise / unvollständig: **${a.tenants_partial_api}**`);
  }
  lines.push("- Readiness-Verteilung:");
  for (const k of ["no_footprint", "early_pilot", "baseline_governance", "advanced_governance"] as const) {
    const n = a.readiness_distribution[k];
    if (n > 0) lines.push(`  - ${GTM_READINESS_LABELS_DE[k]}: ${n}`);
  }
  lines.push(`- Review überfällig / offen: **${a.count_review_stale}**`);
  lines.push(`- Export-Kadenz überschritten (inkl. nie exportiert): **${a.count_export_stale}**`);
  lines.push(`- Mandantenbericht (Board) überfällig: **${a.count_board_report_stale}**`);
  lines.push(`- Noch kein erfasster Export: **${a.count_never_export}**`);
  lines.push(`- Offene Prüfpunkte gesamt: **${a.total_open_points}** (hoch: **${a.total_open_points_hoch}**)`);
  lines.push(`- Attention-Queue: **${a.attention_queue_size}** Mandant(en)`);
  lines.push(`- Offene Reminder: **${a.open_reminders_open_count}** (heute/überfällig: **${a.reminders_due_today_or_overdue_count}**, diese KW: **${a.reminders_due_this_week_open_count}**)`);
  lines.push("");

  lines.push(`## B) Top ${pkg.part_b_top_attention.length} Attention-Mandanten`);
  lines.push("");
  if (pkg.part_b_top_attention.length === 0) {
    lines.push("_Keine Einträge in der Attention-Queue._");
    lines.push("");
  } else {
    for (const q of pkg.part_b_top_attention) {
      lines.push(`### ${q.rank}. ${lineLabel(q)} · Score ${q.attention_score}`);
      lines.push("");
      lines.push("**Warum jetzt?**");
      for (const w of q.warum_jetzt_de) {
        lines.push(`- ${w}`);
      }
      lines.push("");
      lines.push(`**Nächster Schritt:** ${q.naechster_schritt_de}`);
      lines.push("");
    }
  }

  const c = pkg.part_c_changes_since_baseline;
  lines.push("## C) Veränderungen seit letzter Periode (Baseline)");
  lines.push("");
  if (!c.baseline_available) {
    lines.push(
      "_Keine Baseline geladen oder leer – Monats-Baseline unter `data/kanzlei-monthly-report-baseline.json` setzen (z. B. über Monatsreport „Baseline speichern“)._",
    );
    lines.push("");
  } else {
    lines.push(`Baseline: ${c.baseline_saved_at ?? "—"}${c.baseline_period_label ? ` · ${c.baseline_period_label}` : ""}`);
    lines.push("");

    lines.push("### Verbesserungen");
    if (c.improvements.length === 0) {
      lines.push("_Keine zusammengefassten Verbesserungen._");
    } else {
      for (const x of c.improvements) {
        lines.push(`- **${lineLabel(x)}:** ${x.text_de}`);
      }
    }
    lines.push("");

    lines.push("### Verschlechterungen / Mehrlast");
    if (c.deteriorations.length === 0) {
      lines.push("_Keine zusammengefassten Verschlechterungen._");
    } else {
      for (const x of c.deteriorations) {
        lines.push(`- **${lineLabel(x)}:** ${x.text_de}`);
      }
    }
    lines.push("");

    lines.push("### Neu dringlicher / Eskalation");
    if (c.newly_urgent.length === 0) {
      lines.push("_Keine zusätzlichen Eskalationen aus dem Vergleich._");
    } else {
      for (const x of c.newly_urgent) {
        lines.push(`- **${lineLabel(x)}:** ${x.text_de}`);
      }
    }
    lines.push("");
  }

  lines.push("## D) Empfohlene Berater-Prioritäten (nächster Monat / Quartal)");
  lines.push("");
  for (const p of pkg.part_d_recommended_priorities_de) {
    lines.push(`- ${p}`);
  }
  lines.push("");

  const kpi = pkg.part_e_advisor_kpis;
  if (kpi) {
    lines.push("## E) Kanzlei-KPIs (Steuerung)");
    lines.push("");
    lines.push(
      `Fenster **${kpi.window_days}** Tage · ${kpi.mapped_tenant_count} Mandanten · Schema ${kpi.version}.`,
    );
    lines.push("");
    for (const tile of kpi.strip) {
      const tr =
        tile.trend === "up"
          ? "↑"
          : tile.trend === "down"
            ? "↓"
            : tile.trend === "flat"
              ? "→"
              : "○";
      lines.push(`- **${tile.label_de}:** ${tile.value_display_de} ${tr} (${tile.traffic_light})`);
    }
    lines.push("");
  }

  const trd = pkg.part_f_kpi_trends;
  if (trd) {
    lines.push("## F) KPI-Trends (Kurz)");
    lines.push("");
    lines.push(
      `Rolling **${trd.period_label_de}** · Schema ${trd.version} – letzter History-Punkt vs. vorheriger Punkt im Zeitraum.`,
    );
    lines.push("");
    for (const line of trd.narrative_lines_de) {
      lines.push(`- ${line}`);
    }
    lines.push("");
  }

  const sla = pkg.part_g_sla_lagebild;
  lines.push("## G) SLA-Lagebild (Wave 47)");
  lines.push("");
  lines.push(
    `Auswertung **${sla.evaluated_at}** · ${sla.findings.length} Befund(e) · Schema ${sla.version}.`,
  );
  lines.push("");
  for (const s of sla.signals) {
    const mark = s.active ? "(!) " : "";
    lines.push(`- ${mark}**${s.label_de}:** ${s.detail_de}`);
  }
  lines.push("");
  if (sla.findings.length > 0) {
    for (const f of sla.findings.slice(0, 6)) {
      lines.push(`- **${f.title_de}** (${f.severity}): ${f.detail_de}`);
    }
    lines.push("");
  }
  for (const step of sla.next_steps_de.slice(0, 3)) {
    lines.push(`- _Nächster Schritt:_ ${step}`);
  }
  lines.push("");

  const ag = pkg.part_h_ai_governance;
  const ags = ag.summary;
  lines.push("## H) AI-Governance-Steuerung (Wave 48)");
  lines.push("");
  lines.push(`_${ag.disclaimer_de}_`);
  lines.push("");
  lines.push(
    `- Mandanten: **${ags.total_mandanten}** · API teilweise: **${ags.tenants_partial_api}** · Schema ${ag.version}.`,
  );
  lines.push(
    `- Hinweis AI-Act-/Register-Thematik: **${ags.count_likely_ai_act_relevance}** · High-Risk im Dashboard: **${ags.count_potential_high_risk_exposure}**`,
  );
  lines.push(
    `- ISO-42001 Nachholbedarf (schwach/mittel): **${ags.count_weak_iso42001}** · Post-Market-Lücke: **${ags.count_weak_post_market}** · Human Oversight: **${ags.count_weak_human_oversight}**`,
  );
  lines.push("");
  lines.push("### Top Mandanten für Beraterkapazität");
  for (const t of ag.top_attention.slice(0, 8)) {
    lines.push(`- **${lineLabel(t)}:** ${t.priority_hint_de}`);
  }
  lines.push("");

  lines.push("---");
  lines.push("");
  lines.push("### Priorisierung (Kurz)");
  for (const r of m.prioritization_rationale_de) {
    lines.push(`- ${r}`);
  }

  return lines.join("\n");
}
