/**
 * Wave 42 – Markdown für Kanzlei-Monatsreport (DE).
 */

import { GTM_READINESS_LABELS_DE } from "@/lib/gtmAccountReadiness";
import type { KanzleiMonthlyReportDto } from "@/lib/kanzleiMonthlyReportTypes";

function readinessDe(code: string): string {
  return GTM_READINESS_LABELS_DE[code as keyof typeof GTM_READINESS_LABELS_DE] ?? code;
}

export function kanzleiMonthlyReportMarkdownDe(r: KanzleiMonthlyReportDto): string {
  const s1 = r.section_1_portfolio_summary;
  const parts: string[] = [];

  parts.push(`# Kanzlei-Portfolio-Report (${r.period_label})`);
  parts.push(
    `_Erzeugt: ${new Date(r.generated_at).toLocaleString("de-DE")} · Portfolio-Stand: ${new Date(r.portfolio_generated_at).toLocaleString("de-DE")} · Schema ${r.version} / ${r.portfolio_version}_`,
  );

  parts.push(`## 1) Portfolio-Überblick`);
  parts.push(`- Mandanten (gemappt): **${s1.total_mandanten}**`);
  parts.push(`- Backend erreichbar: **${s1.backend_reachable ? "ja" : "teilweise nein"}**`);
  if (s1.tenants_partial_api > 0) {
    parts.push(`- API teilweise ohne vollständige Daten: **${s1.tenants_partial_api}**`);
  }
  parts.push(`- Readiness-Verteilung:`);
  for (const cls of Object.keys(s1.readiness_distribution) as (keyof typeof s1.readiness_distribution)[]) {
    const n = s1.readiness_distribution[cls];
    if (n > 0) parts.push(`  - ${readinessDe(cls)}: **${n}**`);
  }
  parts.push(`- Überfällige / offene Kanzlei-Reviews: **${s1.count_review_stale}**`);
  parts.push(`- Export-Kadenz kritisch (stale / kein Datum): **${s1.count_export_stale}**`);
  parts.push(`- Ohne erfassten Export in Historie: **${s1.count_never_export}**`);
  parts.push(`- Überfälliger Board-/Statusbericht: **${s1.count_board_report_stale}**`);
  parts.push(`- Summe offene Prüfpunkte: **${s1.total_open_points}** (hoch: **${s1.total_open_points_hoch}**)`);
  parts.push(`- Mandanten in Attention-Queue: **${s1.count_queue}**`);

  parts.push(`## 2) Top-Aufmerksamkeit (Handlungsliste)`);
  if (r.section_2_attention_top.length === 0) {
    parts.push(`_Keine Einträge in der Queue (Kriterien nicht erfüllt)._`);
  } else {
    for (const row of r.section_2_attention_top) {
      const name = row.mandant_label ?? row.tenant_id;
      parts.push(
        `${row.rank}. **${name}** (\`${row.tenant_id}\`) – Score ${row.attention_score} – _Nächster Schritt:_ ${row.naechster_schritt_de}`,
      );
    }
  }

  parts.push(`## 3) Veränderungen seit Baseline`);
  const ch = r.section_3_changes;
  if (!r.compared_to_baseline || !ch.baseline_available) {
    parts.push(
      `_Kein Vergleich: Baseline-Datei fehlt oder Vergleich war deaktiviert. Für Monatsvergleiche einmalig Baseline speichern (\`update_baseline=1\` nach Stichtag), danach erneut Report erzeugen._`,
    );
  } else {
    parts.push(
      `_Baseline gespeichert: ${ch.baseline_saved_at ? new Date(ch.baseline_saved_at).toLocaleString("de-DE") : "—"}${ch.baseline_period_label ? ` (Periode ${ch.baseline_period_label})` : ""}_`,
    );
    const sub = (
      title: string,
      items: { tenant_id: string; mandant_label: string | null; text_de: string }[],
    ) => {
      if (items.length === 0) return;
      parts.push(`### ${title}`);
      for (const it of items) {
        const name = it.mandant_label ?? it.tenant_id;
        parts.push(`- **${name}** (\`${it.tenant_id}\`): ${it.text_de}`);
      }
    };
    sub("Readiness verbessert", ch.readiness_improved);
    sub("Readiness zurück", ch.readiness_deteriorated);
    sub("Offene Punkte gestiegen (≥2)", ch.open_points_increased);
    sub("Offene Punkte gesunken (≥2)", ch.open_points_decreased);
    sub("Attention eskaliert", ch.attention_escalated);
    sub("Attention entpannt", ch.attention_eased);
    sub("Kadenz / Ampel-Notizen", ch.cadence_notes);
  }

  parts.push(`## 4) Empfohlene Schwerpunkte`);
  for (const f of r.section_4_focus_areas_de) {
    parts.push(`- ${f}`);
  }

  const kpi = r.section_5_advisor_kpis;
  if (kpi) {
    parts.push(`## 5) Kanzlei-KPIs (Wave 45)`);
    parts.push(
      `_Fenster **${kpi.window_days}** Tage · Schema ${kpi.version} · Median-Reaktionszeiten vs. Vorperiode._`,
    );
    for (const tile of kpi.strip) {
      const tr =
        tile.trend === "up"
          ? "↑"
          : tile.trend === "down"
            ? "↓"
            : tile.trend === "flat"
              ? "→"
              : "○";
      parts.push(
        `- **${tile.label_de}:** ${tile.value_display_de} ${tr} (_Ampel: ${tile.traffic_light}_) — ${tile.hint_de}`,
      );
    }
    parts.push(`### Segment-Überblick (${kpi.segment_by === "readiness" ? "Readiness" : "Branchenlabel"})`);
    for (const s of kpi.segments.slice(0, 6)) {
      parts.push(
        `- **${s.label_de}** (${s.tenant_count}): Review aktuell ${Math.round(s.review_current_share * 100)} % · Export OK ${Math.round(s.export_fresh_share * 100)} % · ohne Reminder ${Math.round(s.share_no_open_reminders * 100)} % · ohne rote Säule ${Math.round(s.share_no_red_pillar * 100)} %`,
      );
    }
  }

  const trd = r.section_6_kpi_trends;
  if (trd) {
    parts.push(`## 6) KPI-Trends (Wave 46)`);
    parts.push(
      `_Rolling **${trd.period_label_de}** · Schema ${trd.version} · Vergleich letzter History-Punkt vs. vorheriger Punkt im Zeitraum._`,
    );
    for (const line of trd.narrative_lines_de) {
      parts.push(`- ${line}`);
    }
  }

  const sla = r.section_7_advisor_sla;
  parts.push(`## 7) SLA & Eskalation (Wave 47)`);
  parts.push(`_Ausgewertet: ${sla.evaluated_at} · ${sla.findings.length} Befund(e) · Schema ${sla.version}._`);
  const activeSig = sla.signals.filter((s) => s.active);
  if (activeSig.length === 0) {
    parts.push(`- Keine aktiven Eskalationssignale.`);
  } else {
    for (const s of activeSig) {
      parts.push(`- **${s.label_de}:** ${s.detail_de}`);
    }
  }
  if (sla.findings.length > 0) {
    for (const f of sla.findings.slice(0, 8)) {
      const sev = f.severity === "critical" ? "kritisch" : f.severity === "warning" ? "Warnung" : "Info";
      parts.push(`- (${sev}) **${f.title_de}** – ${f.detail_de}`);
    }
  }
  for (const step of sla.next_steps_de.slice(0, 4)) {
    parts.push(`- Nächster Schritt: ${step}`);
  }

  const ag = r.section_8_ai_governance;
  const ags = ag.summary;
  parts.push(`## 8) AI-Governance (Wave 48)`);
  parts.push(`_${ag.disclaimer_de}_`);
  parts.push(
    `- Mandanten: **${ags.total_mandanten}** · API teilweise: **${ags.tenants_partial_api}** · Schema ${ag.version}.`,
  );
  parts.push(
    `- Hinweis auf mögliche AI-Act-/Register-Thematik (Heuristik): **${ags.count_likely_ai_act_relevance}** · High-Risk im Dashboard: **${ags.count_potential_high_risk_exposure}**`,
  );
  parts.push(
    `- Schwache ISO-42001-Säule (schwach/mittel): **${ags.count_weak_iso42001}** · Post-Market/Reporting-Lücke: **${ags.count_weak_post_market}** · Prüfbedarf Human Oversight: **${ags.count_weak_human_oversight}**`,
  );
  parts.push(`- EU AI Act (Bucket): schwach **${ags.bucket_ai_act.weak}**, mittel **${ags.bucket_ai_act.medium}**, stark **${ags.bucket_ai_act.strong}**, unbekannt **${ags.bucket_ai_act.unknown}**`);
  parts.push(
    `- ISO 42001 (Bucket): schwach **${ags.bucket_iso42001.weak}**, mittel **${ags.bucket_iso42001.medium}**, stark **${ags.bucket_iso42001.strong}**, unbekannt **${ags.bucket_iso42001.unknown}**`,
  );
  parts.push(`### Top-Fokus Mandanten`);
  if (ag.top_attention.length === 0) {
    parts.push(`- _Keine Mandanten im Überblick._`);
  } else {
    for (const t of ag.top_attention.slice(0, 8)) {
      const name = t.mandant_label ?? t.tenant_id;
      parts.push(`- **${name}** (\`${t.tenant_id}\`): ${t.priority_hint_de}`);
    }
  }

  parts.push(`---`);
  parts.push(
    `Hinweis: Portfolio-Report für interne Kanzlei-Arbeit; keine Board-Tischreife. Daten aus Live-API und lokaler Historie – Änderungslogik bewusst grob (siehe Doku Wave 42).`,
  );

  return parts.join("\n\n");
}
