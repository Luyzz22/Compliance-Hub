/**
 * Wave 42 – Monatsreport aus Portfolio-Payload + optionaler Baseline (ohne server-only).
 */

import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import { GTM_READINESS_LABELS_DE, type GtmReadinessClass } from "@/lib/gtmAccountReadiness";
import type { KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import type { AdvisorKpiTrendsNarrativeBlock } from "@/lib/advisorKpiTrendsBuild";
import type { AdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiTypes";
import type {
  KanzleiAttentionBand,
  KanzleiMonthlyBaselineTenant,
  KanzleiMonthlyChangeLine,
  KanzleiMonthlyReportDto,
  KanzleiMonthlyReportSection1,
  KanzleiMonthlyReportSection3,
} from "@/lib/kanzleiMonthlyReportTypes";
import { KANZLEI_MONTHLY_REPORT_VERSION } from "@/lib/kanzleiMonthlyReportTypes";

const PILLAR_KEYS: BoardReadinessPillarKey[] = ["eu_ai_act", "iso_42001", "nis2", "dsgvo"];

const READINESS_RANK: Record<GtmReadinessClass, number> = {
  no_footprint: 0,
  early_pilot: 1,
  baseline_governance: 2,
  advanced_governance: 3,
};

/** Grobe Attention-Stufen (erklärbar, nicht identisch mit Queue-Schwellen). */
export function attentionBand(score: number): KanzleiAttentionBand {
  if (score >= 55) return "high";
  if (score >= 25) return "medium";
  return "low";
}

export function worstPillarTrafficFromRow(row: KanzleiPortfolioRow): BoardReadinessTraffic {
  let w: BoardReadinessTraffic = "green";
  for (const k of PILLAR_KEYS) {
    const t = row.pillar_traffic[k];
    if (t === "red") return "red";
    if (t === "amber") w = "amber";
  }
  return w;
}

export function rowToBaselineTenant(row: KanzleiPortfolioRow): KanzleiMonthlyBaselineTenant {
  return {
    readiness_class: row.readiness_class,
    attention_score: row.attention_score,
    attention_band: attentionBand(row.attention_score),
    open_points_count: row.open_points_count,
    open_points_hoch: row.open_points_hoch,
    worst_traffic: worstPillarTrafficFromRow(row),
    review_stale: row.review_stale,
    any_export_stale: row.any_export_stale,
    board_report_stale: row.board_report_stale,
    pillar_traffic: { ...row.pillar_traffic },
  };
}

export function summarizeKanzleiMonthlyReportSection1(payload: KanzleiPortfolioPayload): KanzleiMonthlyReportSection1 {
  const readiness_distribution: Record<GtmReadinessClass, number> = {
    no_footprint: 0,
    early_pilot: 0,
    baseline_governance: 0,
    advanced_governance: 0,
  };
  let count_review_stale = 0;
  let count_export_stale = 0;
  let count_board_report_stale = 0;
  let count_never_export = 0;
  let total_open_points = 0;
  let total_open_points_hoch = 0;

  for (const r of payload.rows) {
    readiness_distribution[r.readiness_class] += 1;
    if (r.review_stale) count_review_stale += 1;
    if (r.any_export_stale) count_export_stale += 1;
    if (r.board_report_stale) count_board_report_stale += 1;
    if (r.never_any_export) count_never_export += 1;
    total_open_points += r.open_points_count;
    total_open_points_hoch += r.open_points_hoch;
  }

  return {
    total_mandanten: payload.mapped_tenant_count,
    tenants_partial_api: payload.tenants_partial,
    backend_reachable: payload.backend_reachable,
    readiness_distribution,
    count_review_stale,
    count_export_stale,
    count_board_report_stale,
    count_never_export,
    total_open_points,
    total_open_points_hoch,
    count_queue: payload.attention_queue.length,
  };
}

function line(
  row: KanzleiPortfolioRow,
  text_de: string,
): KanzleiMonthlyChangeLine {
  return { tenant_id: row.tenant_id, mandant_label: row.mandant_label, text_de };
}

export function buildKanzleiMonthlyReportSection3(
  payload: KanzleiPortfolioPayload,
  baseline: { saved_at: string; period_label: string | null; tenants: Record<string, KanzleiMonthlyBaselineTenant> } | null,
): KanzleiMonthlyReportSection3 {
  const empty: KanzleiMonthlyReportSection3 = {
    baseline_available: false,
    baseline_saved_at: null,
    baseline_period_label: null,
    readiness_improved: [],
    readiness_deteriorated: [],
    open_points_increased: [],
    open_points_decreased: [],
    attention_escalated: [],
    attention_eased: [],
    cadence_notes: [],
  };

  if (!baseline || Object.keys(baseline.tenants).length === 0) {
    return empty;
  }

  const out: KanzleiMonthlyReportSection3 = {
    baseline_available: true,
    baseline_saved_at: baseline.saved_at,
    baseline_period_label: baseline.period_label,
    readiness_improved: [],
    readiness_deteriorated: [],
    open_points_increased: [],
    open_points_decreased: [],
    attention_escalated: [],
    attention_eased: [],
    cadence_notes: [],
  };

  for (const row of payload.rows) {
    const b = baseline.tenants[row.tenant_id];
    if (!b) continue;

    const r0 = READINESS_RANK[row.readiness_class];
    const r1 = READINESS_RANK[b.readiness_class];
    if (r0 > r1) {
      out.readiness_improved.push(
        line(
          row,
          `Readiness-Klasse verbessert: ${GTM_READINESS_LABELS_DE[b.readiness_class]} → ${row.readiness_label_de}.`,
        ),
      );
    } else if (r0 < r1) {
      out.readiness_deteriorated.push(
        line(
          row,
          `Readiness-Klasse zurück: ${GTM_READINESS_LABELS_DE[b.readiness_class]} → ${row.readiness_label_de}.`,
        ),
      );
    }

    const d = row.open_points_count - b.open_points_count;
    if (d >= 2) {
      out.open_points_increased.push(
        line(row, `Offene Prüfpunkte deutlich gestiegen: ${b.open_points_count} → ${row.open_points_count} (+${d}).`),
      );
    } else if (d <= -2) {
      out.open_points_decreased.push(
        line(row, `Offene Prüfpunkte deutlich gesunken: ${b.open_points_count} → ${row.open_points_count} (${d}).`),
      );
    }

    const bandNow = attentionBand(row.attention_score);
    const bandWas = b.attention_band;
    const rankBand: Record<KanzleiAttentionBand, number> = { low: 0, medium: 1, high: 2 };
    if (rankBand[bandNow] > rankBand[bandWas]) {
      out.attention_escalated.push(
        line(
          row,
          `Attention höher: Band ${bandWas} → ${bandNow} (Score ${b.attention_score} → ${row.attention_score}).`,
        ),
      );
    } else if (rankBand[bandNow] < rankBand[bandWas]) {
      out.attention_eased.push(
        line(
          row,
          `Attention niedriger: Band ${bandWas} → ${bandNow} (Score ${b.attention_score} → ${row.attention_score}).`,
        ),
      );
    }

    if (!b.review_stale && row.review_stale) {
      out.cadence_notes.push(line(row, "Review-Kadenz: zuvor im Zeitraum, jetzt überfällig / offen."));
    } else if (b.review_stale && !row.review_stale) {
      out.cadence_notes.push(line(row, "Review-Kadenz: überfällig → wieder im Zeitraum (Review nachgezogen)."));
    }
    if (!b.any_export_stale && row.any_export_stale) {
      out.cadence_notes.push(line(row, "Export-Kadenz: jetzt überschritten oder kein gültiger Zeitstempel."));
    } else if (b.any_export_stale && !row.any_export_stale) {
      out.cadence_notes.push(line(row, "Export-Kadenz: wieder im Zeitraum (frischer Export erfasst)."));
    }

    const w0 = worstPillarTrafficFromRow(row);
    const w1 = b.worst_traffic;
    const wr: Record<BoardReadinessTraffic, number> = { green: 2, amber: 1, red: 0 };
    if (wr[w0] < wr[w1]) {
      out.attention_escalated.push(
        line(row, `Schlechteste Säulen-Ampel verschlechtert: ${w1} → ${w0}.`),
      );
    } else if (wr[w0] > wr[w1]) {
      out.attention_eased.push(line(row, `Schlechteste Säulen-Ampel verbessert: ${w1} → ${w0}.`));
    }
  }

  const cap = 12;
  out.readiness_improved = out.readiness_improved.slice(0, cap);
  out.readiness_deteriorated = out.readiness_deteriorated.slice(0, cap);
  out.open_points_increased = out.open_points_increased.slice(0, cap);
  out.open_points_decreased = out.open_points_decreased.slice(0, cap);
  out.attention_escalated = out.attention_escalated.slice(0, cap);
  out.attention_eased = out.attention_eased.slice(0, cap);
  out.cadence_notes = out.cadence_notes.slice(0, cap);

  return out;
}

export function buildKanzleiPortfolioFocusAreasDe(
  payload: KanzleiPortfolioPayload,
  s1: KanzleiMonthlyReportSection1,
): string[] {
  const rows = payload.rows;
  let euRed = 0;
  let euAmber = 0;
  let isoRed = 0;
  let nisRed = 0;
  let nisAmber = 0;
  let dsgvoRed = 0;
  let apiBad = 0;
  let gapsHeavy = 0;

  for (const r of rows) {
    if (r.pillar_traffic.eu_ai_act === "red") euRed += 1;
    else if (r.pillar_traffic.eu_ai_act === "amber") euAmber += 1;
    if (r.pillar_traffic.iso_42001 === "red") isoRed += 1;
    if (r.pillar_traffic.nis2 === "red") nisRed += 1;
    else if (r.pillar_traffic.nis2 === "amber") nisAmber += 1;
    if (r.pillar_traffic.dsgvo === "red") dsgvoRed += 1;
    if (!r.api_fetch_ok) apiBad += 1;
    if (r.gaps_heavy_without_recent_export) gapsHeavy += 1;
  }

  const out: string[] = [];

  if (s1.count_export_stale > 0 || s1.count_never_export > 0) {
    out.push(
      `Export- und Dokumentationskadenz: ${s1.count_export_stale} Mandant(en) mit überschrittener Export-Kadenz, ${s1.count_never_export} ohne erfassten Export – Readiness- oder DATEV-Export planen.`,
    );
  }
  if (s1.count_review_stale > 0) {
    out.push(
      `${s1.count_review_stale} Mandant(en) mit überfälligem oder fehlendem Kanzlei-Review – Termine im Playbook-Zyklus einplanen.`,
    );
  }
  if (s1.count_board_report_stale > 0) {
    out.push(
      `${s1.count_board_report_stale} Mandant(en) mit überfälligem Board-/Statusbericht – Daten im Mandanten aktualisieren.`,
    );
  }
  if (euRed > 0 || euAmber > 0) {
    out.push(
      `EU AI Act: ${euRed} rot, ${euAmber} gelb – Register, Dokumentation und High-Risk-Bewertungen priorisieren.`,
    );
  }
  if (isoRed > 0) {
    out.push(`ISO 42001: ${isoRed} Mandant(en) mit roter Ampel – AIMs-Nachweise und Rollen klären.`);
  }
  if (nisRed > 0 || nisAmber > 0) {
    out.push(
      `NIS2: ${nisRed} rot, ${nisAmber} gelb – Lieferketten- und Meldepfade bei betroffenen Mandanten schärfen.`,
    );
  }
  if (dsgvoRed > 0) {
    out.push(`DSGVO: ${dsgvoRed} Mandant(en) rot – Verarbeitungsverzeichnis, VVT-Erweiterungen und Verträge prüfen.`);
  }
  if (gapsHeavy > 0) {
    out.push(
      `${gapsHeavy} Mandant(en) mit vielen offenen Punkten ohne frischen Export – vor Gespräch Export für die Kanzlei-Akte ziehen.`,
    );
  }
  if (apiBad > 0) {
    out.push(`${apiBad} Mandant(en) mit unvollständiger API-Lesbarkeit – Zugriff/Keys prüfen, sonst kein belastbarer Report.`);
  }

  if (out.length === 0) {
    out.push("Keine dominante Schwerpunktsignale im Aggregat – Queue und Einzelfälle im Cockpit prüfen.");
  }

  return out.slice(0, 8);
}

export type BuildMonthlyReportOptions = {
  periodLabel: string;
  /** Wenn false, wird Abschnitt 3 ohne Vergleich ausgegeben (leer außer Metainfo). */
  compareToBaseline: boolean;
  attentionTopN: number;
  /** Wave 45 – optionaler KPI-Block (Abschnitt 5). */
  advisorKpiSnapshot?: AdvisorKpiPortfolioSnapshot | null;
  /** Wave 46 – optionaler Trend-Kurzblock (Abschnitt 6). */
  kpiTrendsNarrative?: AdvisorKpiTrendsNarrativeBlock | null;
};

export function buildKanzleiMonthlyReport(
  payload: KanzleiPortfolioPayload,
  baseline: {
    saved_at: string;
    period_label: string | null;
    tenants: Record<string, KanzleiMonthlyBaselineTenant>;
  } | null,
  opts: BuildMonthlyReportOptions,
): KanzleiMonthlyReportDto {
  const s1 = summarizeKanzleiMonthlyReportSection1(payload);
  const top = payload.attention_queue.slice(0, opts.attentionTopN).map((q, i) => ({
    rank: i + 1,
    tenant_id: q.tenant_id,
    mandant_label: q.mandant_label,
    attention_score: q.attention_score,
    naechster_schritt_de: q.naechster_schritt_de,
  }));

  const s3: KanzleiMonthlyReportSection3 = opts.compareToBaseline
    ? buildKanzleiMonthlyReportSection3(payload, baseline)
    : {
        baseline_available: false,
        baseline_saved_at: baseline?.saved_at ?? null,
        baseline_period_label: baseline?.period_label ?? null,
        readiness_improved: [],
        readiness_deteriorated: [],
        open_points_increased: [],
        open_points_decreased: [],
        attention_escalated: [],
        attention_eased: [],
        cadence_notes: [],
      };

  return {
    version: KANZLEI_MONTHLY_REPORT_VERSION,
    generated_at: new Date().toISOString(),
    period_label: opts.periodLabel,
    portfolio_version: payload.version,
    portfolio_generated_at: payload.generated_at,
    compared_to_baseline: opts.compareToBaseline && Boolean(baseline && Object.keys(baseline.tenants).length > 0),
    section_1_portfolio_summary: s1,
    section_2_attention_top: top,
    section_3_changes: s3,
    section_4_focus_areas_de: buildKanzleiPortfolioFocusAreasDe(payload, s1),
    section_5_advisor_kpis: opts.advisorKpiSnapshot ?? null,
    section_6_kpi_trends: opts.kpiTrendsNarrative ?? null,
  };
}
