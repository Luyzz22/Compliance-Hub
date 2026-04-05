/**
 * Wave 45 – KPI-Aggregation aus Portfolio, Historie-Zeilen und Reminder-Store (ohne server-only).
 */

import { GTM_READINESS_LABELS_DE, type GtmReadinessClass } from "@/lib/gtmAccountReadiness";
import type { BoardReadinessPillarKey } from "@/lib/boardReadinessTypes";
import type { MandantReminderRecord } from "@/lib/advisorMandantReminderTypes";
import type {
  AdvisorKpiPortfolioSnapshot,
  AdvisorKpiSegmentBreakdown,
  AdvisorKpiStripItem,
  AdvisorKpiTraffic,
  AdvisorKpiTrend,
  BuildAdvisorKpiPortfolioInput,
} from "@/lib/advisorKpiTypes";
import { ADVISOR_KPI_PORTFOLIO_VERSION } from "@/lib/advisorKpiTypes";
import type { KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import { daysSinceValidIso, isParseableIso, maxIsoTimestamps } from "@/lib/mandantHistoryMerge";

const PILLAR_KEYS: BoardReadinessPillarKey[] = ["eu_ai_act", "iso_42001", "nis2", "dsgvo"];

function median(nums: number[]): number | null {
  if (nums.length === 0) return null;
  const s = [...nums].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 === 1 ? s[m]! : (s[m - 1]! + s[m]!) / 2;
}

function rowHasRedPillar(row: KanzleiPortfolioRow): boolean {
  return PILLAR_KEYS.some((k) => row.pillar_traffic[k] === "red");
}

function lastExportIso(row: KanzleiPortfolioRow): string | null {
  return maxIsoTimestamps(row.last_mandant_readiness_export_at, row.last_datev_bundle_export_at);
}

function inMsRange(iso: string, startMs: number, endMs: number): boolean {
  if (!isParseableIso(iso)) return false;
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return false;
  return t >= startMs && t <= endMs;
}

function resolutionHoursMs(r: MandantReminderRecord): number | null {
  const u = Date.parse(r.updated_at);
  const c = Date.parse(r.created_at);
  if (Number.isNaN(u) || Number.isNaN(c) || u < c) return null;
  return (u - c) / (60 * 60 * 1000);
}

function closedInWindow(
  reminders: MandantReminderRecord[],
  startMs: number,
  endMs: number,
  categoryFilter?: MandantReminderRecord["category"],
): number[] {
  const hours: number[] = [];
  for (const r of reminders) {
    if (r.status === "open") continue;
    if (categoryFilter !== undefined && r.category !== categoryFilter) continue;
    const u = Date.parse(r.updated_at);
    if (Number.isNaN(u) || u < startMs || u > endMs) continue;
    const h = resolutionHoursMs(r);
    if (h !== null) hours.push(h);
  }
  return hours;
}

function shareTraffic(share: number, greenAt: number, amberAt: number): AdvisorKpiTraffic {
  if (share >= greenAt) return "green";
  if (share >= amberAt) return "amber";
  return "red";
}

/** Niedrigere Median-Stunden = besser (schnellere Reaktion). */
function hoursTraffic(h: number | null): AdvisorKpiTraffic {
  if (h === null) return "neutral";
  if (h <= 72) return "green";
  if (h <= 168) return "amber";
  return "red";
}

function trendNumeric(
  current: number | null,
  previous: number | null,
  lowerIsBetter: boolean,
): AdvisorKpiTrend {
  if (current === null || previous === null) return "unknown";
  const eps = 1e-6;
  if (Math.abs(current - previous) < eps) return "flat";
  const improved = lowerIsBetter ? current < previous : current > previous;
  return improved ? "up" : "down";
}

function trendShare(current: number, previous: number): AdvisorKpiTrend {
  const d = current - previous;
  if (Math.abs(d) < 0.02) return "flat";
  return d > 0 ? "up" : "down";
}

function formatPct(x: number): string {
  return `${Math.round(x * 100)} %`;
}

function buildSegments(
  rows: KanzleiPortfolioRow[],
  segmentBy: "readiness" | "primary_segment",
): AdvisorKpiSegmentBreakdown[] {
  const buckets = new Map<string, KanzleiPortfolioRow[]>();
  for (const row of rows) {
    const key =
      segmentBy === "readiness"
        ? row.readiness_class
        : row.primary_segment_label_de ?? "__none__";
    const arr = buckets.get(key) ?? [];
    arr.push(row);
    buckets.set(key, arr);
  }
  const out: AdvisorKpiSegmentBreakdown[] = [];
  for (const [key, list] of buckets) {
    const n = list.length;
    if (n === 0) continue;
    const label_de =
      segmentBy === "readiness"
        ? GTM_READINESS_LABELS_DE[key as GtmReadinessClass] ?? key
        : key === "__none__"
          ? "Ohne Branchen-Label"
          : key;
    const reviewOk = list.filter((r) => !r.review_stale).length;
    const exportOk = list.filter((r) => !r.any_export_stale).length;
    const noRem = list.filter((r) => r.open_reminders_count === 0).length;
    const noRed = list.filter((r) => !rowHasRedPillar(r)).length;
    out.push({
      segment_key: key,
      label_de,
      tenant_count: n,
      review_current_share: reviewOk / n,
      export_fresh_share: exportOk / n,
      share_no_open_reminders: noRem / n,
      share_no_red_pillar: noRed / n,
    });
  }
  out.sort((a, b) => b.tenant_count - a.tenant_count);
  return out;
}

export function buildAdvisorKpiPortfolioSnapshot(
  input: BuildAdvisorKpiPortfolioInput,
): AdvisorKpiPortfolioSnapshot {
  const { payload, reminders, nowMs } = input;
  const windowDays = Math.min(365, Math.max(7, Math.floor(input.windowDays)));
  const windowMs = windowDays * 24 * 60 * 60 * 1000;
  const segmentBy = input.segmentBy ?? "readiness";
  const rows = payload.rows;
  const n = rows.length || 1;

  const curStart = nowMs - windowMs;
  const prevStart = nowMs - 2 * windowMs;
  const prevEnd = curStart;

  let reviewOk = 0;
  let ageSum = 0;
  let ageN = 0;
  let reviewsWin = 0;
  let reviewsPrev = 0;
  let exportOk = 0;
  let exportTouchedWin = 0;
  let exportTouchedPrev = 0;
  let noOpenRem = 0;
  let noRed = 0;

  for (const row of rows) {
    if (!row.review_stale) reviewOk += 1;
    const d = daysSinceValidIso(row.last_review_marked_at, nowMs);
    if (d !== null) {
      ageSum += d;
      ageN += 1;
    }
    if (row.last_review_marked_at && inMsRange(row.last_review_marked_at, curStart, nowMs)) {
      reviewsWin += 1;
    }
    if (row.last_review_marked_at && inMsRange(row.last_review_marked_at, prevStart, prevEnd)) {
      reviewsPrev += 1;
    }
    if (!row.any_export_stale) exportOk += 1;
    const ex = lastExportIso(row);
    if (ex && inMsRange(ex, curStart, nowMs)) exportTouchedWin += 1;
    if (ex && inMsRange(ex, prevStart, prevEnd)) exportTouchedPrev += 1;
    if (row.open_reminders_count === 0) noOpenRem += 1;
    if (!rowHasRedPillar(row)) noRed += 1;
  }

  const reviewShare = n > 0 ? reviewOk / n : 0;
  const exportShare = n > 0 ? exportOk / n : 0;
  const exportTouchedShare = n > 0 ? exportTouchedWin / n : 0;
  const exportTouchedPrevShare = n > 0 ? exportTouchedPrev / n : 0;
  const meanAge = ageN > 0 ? ageSum / ageN : null;

  const remHours = closedInWindow(reminders, curStart, nowMs);
  const remHoursPrev = closedInWindow(reminders, prevStart, prevEnd);
  const attHours = closedInWindow(reminders, curStart, nowMs, "portfolio_attention");
  const attHoursPrev = closedInWindow(reminders, prevStart, prevEnd, "portfolio_attention");

  const medRem = median(remHours);
  const medRemPrev = median(remHoursPrev);
  const medAtt = median(attHours);
  const medAttPrev = median(attHoursPrev);

  const shareNoRem = n > 0 ? noOpenRem / n : 0;
  const shareNoRed = n > 0 ? noRed / n : 0;

  const segments = buildSegments(rows, segmentBy);

  const COCKPIT = "/admin/advisor-portfolio";

  const reviewActivityShare = n > 0 ? reviewsWin / n : 0;
  const reviewActivityPrevShare = n > 0 ? reviewsPrev / n : 0;

  const strip: AdvisorKpiStripItem[] = [
    {
      id: "review_coverage",
      label_de: "Review aktuell",
      value_display_de: formatPct(reviewShare),
      numeric_value: reviewShare,
      unit: "ratio",
      traffic_light: shareTraffic(reviewShare, 0.75, 0.5),
      trend: trendShare(reviewActivityShare, reviewActivityPrevShare),
      href: `${COCKPIT}#kanzlei-kpi-review`,
      hint_de: `Anteil Mandanten ohne überfälliges Kanzlei-Review (Schwelle ${payload.constants.review_stale_days} Tage). Trend: Review-Zeitstempel im Fenster vs. Vorperiode.`,
    },
    {
      id: "export_fresh",
      label_de: "Export-Kadenz OK",
      value_display_de: formatPct(exportShare),
      numeric_value: exportShare,
      unit: "ratio",
      traffic_light: shareTraffic(exportShare, 0.7, 0.45),
      trend: trendShare(exportTouchedShare, exportTouchedPrevShare),
      href: `${COCKPIT}#kanzlei-kpi-export`,
      hint_de: `Anteil mit gültigem letztem Readiness-/DATEV-Export (max. ${payload.constants.any_export_max_age_days} Tage).`,
    },
    {
      id: "reminder_resolution",
      label_de: "Reminder-Reaktionszeit (Median)",
      value_display_de: medRem !== null ? `${medRem.toFixed(1)} h` : "—",
      numeric_value: medRem,
      unit: "hours",
      traffic_light: hoursTraffic(medRem),
      trend: trendNumeric(medRem, medRemPrev, true),
      href: `${COCKPIT}#kanzlei-kpi-reminders`,
      hint_de: `Median Stunden von Reminder-Anlage bis Erledigt/Zurückstellen (letzte ${windowDays} Tage, n=${remHours.length}).`,
    },
    {
      id: "attention_proxy",
      label_de: "Queue-Reminder (Median)",
      value_display_de: medAtt !== null ? `${medAtt.toFixed(1)} h` : "—",
      numeric_value: medAtt,
      unit: "hours",
      traffic_light: hoursTraffic(medAtt),
      trend: trendNumeric(medAtt, medAttPrev, true),
      href: `${COCKPIT}#kanzlei-kpi-queue`,
      hint_de:
        "Proxy für Attention-Bearbeitung: Auto-Reminder „Portfolio-Aufmerksamkeit“ von Anlage bis Abschluss (kein separates Queue-Event-Log).",
    },
    {
      id: "hygiene_red_pillar",
      label_de: "Ohne rote Säule",
      value_display_de: formatPct(shareNoRed),
      numeric_value: shareNoRed,
      unit: "ratio",
      traffic_light: shareTraffic(shareNoRed, 0.8, 0.6),
      trend: "unknown",
      href: `${COCKPIT}#kanzlei-kpi-table`,
      hint_de: "Anteil Mandanten ohne rote Board-Readiness-Säule (EU AI Act, ISO 42001, NIS2, DSGVO).",
    },
  ];

  const interpretation_notes_de = [
    `Fenster: letzte ${windowDays} Tage; Vorperiode davor (gleiche Länge) für Median- und Export-Aktivitätsvergleiche.`,
    "Echte „Anzahl Exporte“ pro Zeitraum ist ohne Event-Log nicht verfügbar – genutzt wird der Anteil Mandanten mit Exportzeitstempel im Fenster.",
    "Attention-Queue selbst wird nicht zeitgestempelt; der Median für „Portfolio-Aufmerksamkeit“-Reminder dient als pragmatischer Proxy.",
  ];

  return {
    version: ADVISOR_KPI_PORTFOLIO_VERSION,
    generated_at: new Date(nowMs).toISOString(),
    window_days: windowDays,
    portfolio_version: payload.version,
    portfolio_generated_at: payload.generated_at,
    mapped_tenant_count: payload.mapped_tenant_count,
    segment_by: segmentBy,
    constants: {
      review_stale_days: payload.constants.review_stale_days,
      any_export_max_age_days: payload.constants.any_export_max_age_days,
    },
    review: {
      current_share: reviewShare,
      mean_age_days: meanAge,
      reviews_touched_in_window: reviewsWin,
      reviews_touched_prev_window: reviewsPrev,
    },
    export_kpis: {
      fresh_share: exportShare,
      export_touched_in_window_share: exportTouchedShare,
      export_touched_prev_window_count: exportTouchedPrev,
    },
    responsiveness: {
      reminder_median_resolution_hours: medRem,
      reminder_median_prev_window_hours: medRemPrev,
      attention_proxy_median_hours: medAtt,
      attention_proxy_prev_median_hours: medAttPrev,
      closed_reminders_in_window: remHours.length,
    },
    hygiene: {
      share_no_open_reminders: shareNoRem,
      share_no_red_pillar: shareNoRed,
    },
    segments,
    strip,
    interpretation_notes_de,
  };
}
