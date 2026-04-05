/**
 * Wave 46 – Persistierte KPI-Zeitpunkte (kein BI-Warehouse).
 */

export const ADVISOR_KPI_HISTORY_FILE_VERSION = "wave46-v1";

/** Ein gespeicherter Querschnitt (typisch einmal pro Kalendertag). */
export type AdvisorKpiHistoryPoint = {
  captured_at: string;
  mapped_tenant_count: number;
  /** Fenster für Median-Reaktionszeit beim Speichern (z. B. 90). */
  kpi_window_days: number;
  review_current_share: number;
  export_fresh_share: number;
  open_reminders_open_count: number;
  share_no_open_reminders: number;
  share_no_red_pillar: number;
  reminder_median_resolution_hours: number | null;
};

export type AdvisorKpiHistoryState = {
  version: typeof ADVISOR_KPI_HISTORY_FILE_VERSION;
  snapshots: AdvisorKpiHistoryPoint[];
};
