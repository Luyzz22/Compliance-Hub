/**
 * Wave 45 – Advisor-/Kanzlei-KPIs (intern, operatives Steering).
 */

import type { MandantReminderRecord } from "@/lib/advisorMandantReminderTypes";
import type { KanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioTypes";

export const ADVISOR_KPI_PORTFOLIO_VERSION = "wave45-v1";

export type AdvisorKpiTrend = "up" | "down" | "flat" | "unknown";

export type AdvisorKpiTraffic = "green" | "amber" | "red" | "neutral";

/** Kompakte Kachel für Cockpit-Strip und Querverweise. */
export type AdvisorKpiStripItem = {
  id: string;
  label_de: string;
  value_display_de: string;
  numeric_value: number | null;
  unit: "ratio" | "days" | "hours" | "count";
  traffic_light: AdvisorKpiTraffic;
  trend: AdvisorKpiTrend;
  /** Relativer Hash auf derselben Seite oder Admin-Pfad mit Hash. */
  href: string | null;
  hint_de: string;
};

export type AdvisorKpiSegmentBreakdown = {
  segment_key: string;
  label_de: string;
  tenant_count: number;
  review_current_share: number;
  export_fresh_share: number;
  share_no_open_reminders: number;
  share_no_red_pillar: number;
};

export type AdvisorKpiPortfolioSnapshot = {
  version: typeof ADVISOR_KPI_PORTFOLIO_VERSION;
  generated_at: string;
  window_days: number;
  portfolio_version: string;
  portfolio_generated_at: string;
  mapped_tenant_count: number;
  segment_by: "readiness" | "primary_segment";
  constants: {
    review_stale_days: number;
    any_export_max_age_days: number;
  };
  review: {
    current_share: number;
    mean_age_days: number | null;
    /** Mandanten mit last_review im Fenster (Proxy für Review-Aktivität). */
    reviews_touched_in_window: number;
    reviews_touched_prev_window: number;
  };
  export_kpis: {
    fresh_share: number;
    /** Anteil Mandanten, deren letzter Export (Readiness/DATEV) im Fenster liegt. */
    export_touched_in_window_share: number;
    export_touched_prev_window_count: number;
  };
  responsiveness: {
    /** Alle geschlossenen Reminder im Fenster (done/dismissed). */
    reminder_median_resolution_hours: number | null;
    reminder_median_prev_window_hours: number | null;
    /** Nur Kategorie portfolio_attention (Proxy: Queue-Signal → Abschluss). */
    attention_proxy_median_hours: number | null;
    attention_proxy_prev_median_hours: number | null;
    closed_reminders_in_window: number;
  };
  hygiene: {
    share_no_open_reminders: number;
    share_no_red_pillar: number;
  };
  segments: AdvisorKpiSegmentBreakdown[];
  strip: AdvisorKpiStripItem[];
  interpretation_notes_de: string[];
};

export type BuildAdvisorKpiPortfolioInput = {
  payload: KanzleiPortfolioPayload;
  reminders: MandantReminderRecord[];
  nowMs: number;
  windowDays: number;
  segmentBy?: "readiness" | "primary_segment";
};
