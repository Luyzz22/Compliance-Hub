/**
 * Wave 46 – KPI-Trends aus History-Punkten (ohne server-only).
 */

import type { AdvisorKpiHistoryPoint } from "@/lib/advisorKpiHistoryTypes";

export const ADVISOR_KPI_TRENDS_VERSION = "wave46-v1";

export type AdvisorKpiTrendPeriod = "4w" | "3m" | "qtd";

export type AdvisorKpiTrendDirection = "up" | "down" | "flat" | "unknown";

export type AdvisorKpiTrendSeriesPoint = {
  /** ISO-Datum (Tag) für Achse */
  t: string;
  v: number | null;
};

export type AdvisorKpiTrendMetric = {
  id: string;
  label_de: string;
  unit: "ratio" | "hours" | "count";
  lower_is_better: boolean;
  current_value: number | null;
  previous_value: number | null;
  direction: AdvisorKpiTrendDirection;
  delta_display_de: string | null;
  series: AdvisorKpiTrendSeriesPoint[];
};

export type AdvisorKpiTrendsDto = {
  version: typeof ADVISOR_KPI_TRENDS_VERSION;
  period: AdvisorKpiTrendPeriod;
  period_label_de: string;
  history_points_in_period: number;
  /** Wave 46: Zeitreihe nur portfolio-weit; Segment-Filter dokumentieren. */
  segment_note_de: string | null;
  metrics: AdvisorKpiTrendMetric[];
  narrative_lines_de: string[];
};

/** Kompakter Block für Monatsreport / Partner-Paket (ohne Serien). */
export type AdvisorKpiTrendsNarrativeBlock = Pick<
  AdvisorKpiTrendsDto,
  "version" | "period" | "period_label_de" | "narrative_lines_de"
>;

export function advisorKpiTrendsNarrativeBlock(dto: AdvisorKpiTrendsDto): AdvisorKpiTrendsNarrativeBlock {
  return {
    version: dto.version,
    period: dto.period,
    period_label_de: dto.period_label_de,
    narrative_lines_de: dto.narrative_lines_de,
  };
}

export type BuildAdvisorKpiTrendsInput = {
  history: AdvisorKpiHistoryPoint[];
  period: AdvisorKpiTrendPeriod;
  nowMs: number;
  /** Wenn gesetzt und nicht "all", Hinweis ausgeben (keine separaten Serien). */
  segment_filter?: string | null;
};

const DAY = 24 * 60 * 60 * 1000;

function periodStartMs(period: AdvisorKpiTrendPeriod, nowMs: number): number {
  const d = new Date(nowMs);
  if (period === "4w") return nowMs - 28 * DAY;
  if (period === "3m") return nowMs - 92 * DAY;
  const y = d.getUTCFullYear();
  const m = d.getUTCMonth();
  const q0 = Math.floor(m / 3) * 3;
  return Date.UTC(y, q0, 1, 12, 0, 0, 0);
}

function periodLabelDe(period: AdvisorKpiTrendPeriod): string {
  if (period === "4w") return "Letzte 4 Wochen";
  if (period === "3m") return "Letzte 3 Monate";
  return "Quartal bis heute (QTD)";
}

function filterHistory(points: AdvisorKpiHistoryPoint[], startMs: number, nowMs: number): AdvisorKpiHistoryPoint[] {
  return points.filter((p) => {
    const t = Date.parse(p.captured_at);
    if (Number.isNaN(t)) return false;
    return t >= startMs && t <= nowMs;
  });
}

function pickSeries(
  points: AdvisorKpiHistoryPoint[],
  getter: (p: AdvisorKpiHistoryPoint) => number | null,
): AdvisorKpiTrendSeriesPoint[] {
  return points.map((p) => ({
    t: p.captured_at.slice(0, 10),
    v: getter(p),
  }));
}

function directionForMetric(
  cur: number | null,
  prev: number | null,
  lowerIsBetter: boolean,
): AdvisorKpiTrendDirection {
  if (cur === null || prev === null) return "unknown";
  const eps = 1e-9;
  if (Math.abs(cur - prev) < eps) return "flat";
  const improved = lowerIsBetter ? cur < prev : cur > prev;
  return improved ? "up" : "down";
}

function deltaDe(
  cur: number | null,
  prev: number | null,
  unit: "ratio" | "hours" | "count",
): string | null {
  if (cur === null || prev === null) return null;
  const d = cur - prev;
  if (unit === "ratio") {
    const pp = Math.round(d * 100);
    return pp === 0 ? "±0 PP" : pp > 0 ? `+${pp} PP` : `${pp} PP`;
  }
  if (unit === "hours") {
    return d === 0 ? "±0 h" : d > 0 ? `+${d.toFixed(1)} h` : `${d.toFixed(1)} h`;
  }
  const n = Math.round(d);
  return n === 0 ? "±0" : n > 0 ? `+${n}` : `${n}`;
}

function buildMetric(
  id: string,
  label_de: string,
  unit: "ratio" | "hours" | "count",
  lower_is_better: boolean,
  series: AdvisorKpiTrendSeriesPoint[],
): AdvisorKpiTrendMetric {
  const valid = series.filter((s) => s.v !== null) as { t: string; v: number }[];
  const last = valid.length >= 1 ? valid[valid.length - 1]!.v : null;
  const prev = valid.length >= 2 ? valid[valid.length - 2]!.v : null;
  return {
    id,
    label_de,
    unit,
    lower_is_better,
    current_value: last,
    previous_value: prev,
    direction: directionForMetric(last, prev, lower_is_better),
    delta_display_de: deltaDe(last, prev, unit),
    series,
  };
}

export function buildKpiTrendNarrativeLinesDe(metrics: AdvisorKpiTrendMetric[]): string[] {
  const out: string[] = [];
  const byId = new Map(metrics.map((m) => [m.id, m]));

  const review = byId.get("review_coverage");
  if (review && review.direction === "up" && review.unit === "ratio") {
    out.push("Review-Deckung im Vergleich zum vorherigen History-Punkt gestiegen.");
  } else if (review && review.direction === "down" && review.unit === "ratio") {
    out.push("Review-Deckung gesunken – Kadenz und Historie prüfen.");
  }

  const exp = byId.get("export_fresh");
  if (exp && exp.direction === "up") {
    out.push("Export-Kadenz (Anteil „frisch“) verbessert.");
  } else if (exp && exp.direction === "down") {
    out.push("Export-Kadenz verschlechtert – Readiness-/DATEV-Exporte einplanen.");
  }

  const rem = byId.get("open_reminders");
  if (rem && rem.direction === "up") {
    out.push("Offene Reminder reduziert.");
  } else if (rem && rem.direction === "down") {
    out.push("Offene Reminder zugenommen – Follow-up und Queue prüfen.");
  }

  const hy = byId.get("no_red_pillar");
  if (hy && hy.direction === "up") {
    out.push("Anteil Mandanten ohne rote Säule gestiegen (Hygiene).");
  } else if (hy && hy.direction === "down") {
    out.push("Anteil ohne rote Säule gesunken – Fokus-Säulen in der Tabelle ansehen.");
  }

  const med = byId.get("reminder_median_hours");
  if (med && med.direction === "up" && med.current_value !== null) {
    out.push("Median-Reaktionszeit auf Reminder kürzer geworden (positiv).");
  } else if (med && med.direction === "down" && med.current_value !== null) {
    out.push("Median-Reaktionszeit auf Reminder länger – Engpässe im Team klären.");
  }

  if (out.length === 0) {
    out.push("Noch zu wenige History-Punkte im gewählten Zeitraum für belastbare Trend-Sätze (täglich ein Punkt empfohlen).");
  }

  return out.slice(0, 6);
}

export function buildAdvisorKpiTrendsDto(input: BuildAdvisorKpiTrendsInput): AdvisorKpiTrendsDto {
  const { history, period, nowMs } = input;
  const start = periodStartMs(period, nowMs);
  const filtered = filterHistory([...history].sort((a, b) => Date.parse(a.captured_at) - Date.parse(b.captured_at)), start, nowMs);

  const seg = input.segment_filter?.trim();
  const segment_note_de =
    seg && seg !== "" && seg.toLowerCase() !== "all"
      ? "Hinweis: Die Zeitreihe ist portfolio-weit. Segment-spezifische History ist in Wave 46 nicht persistiert."
      : null;

  const metrics: AdvisorKpiTrendMetric[] = [
    buildMetric(
      "review_coverage",
      "Review aktuell (Anteil)",
      "ratio",
      false,
      pickSeries(filtered, (p) => p.review_current_share),
    ),
    buildMetric(
      "export_fresh",
      "Export-Kadenz OK (Anteil)",
      "ratio",
      false,
      pickSeries(filtered, (p) => p.export_fresh_share),
    ),
    buildMetric(
      "open_reminders",
      "Offene Reminder (Anzahl)",
      "count",
      true,
      pickSeries(filtered, (p) => p.open_reminders_open_count),
    ),
    buildMetric(
      "no_open_reminders_share",
      "Ohne offene Reminder (Anteil)",
      "ratio",
      false,
      pickSeries(filtered, (p) => p.share_no_open_reminders),
    ),
    buildMetric(
      "no_red_pillar",
      "Ohne rote Säule (Anteil)",
      "ratio",
      false,
      pickSeries(filtered, (p) => p.share_no_red_pillar),
    ),
    buildMetric(
      "reminder_median_hours",
      "Reminder-Median (h, Fenster wie beim Snapshot)",
      "hours",
      true,
      pickSeries(filtered, (p) => p.reminder_median_resolution_hours),
    ),
  ];

  const narrative_lines_de = buildKpiTrendNarrativeLinesDe(metrics);

  return {
    version: ADVISOR_KPI_TRENDS_VERSION,
    period,
    period_label_de: periodLabelDe(period),
    history_points_in_period: filtered.length,
    segment_note_de,
    metrics,
    narrative_lines_de,
  };
}
