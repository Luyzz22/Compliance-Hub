/**
 * Wave 39–41 – Kanzlei-Portfolio-Cockpit (intern, Mehrmandanten-Übersicht).
 */

import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";
import type { GtmReadinessClass } from "@/lib/gtmAccountReadiness";

export const KANZLEI_PORTFOLIO_VERSION = "wave41-v1";

export type KanzleiPortfolioPillarFilter = BoardReadinessPillarKey | "all";

export type KanzleiPortfolioReadinessFilter = GtmReadinessClass | "all";

export type KanzleiPortfolioRow = {
  tenant_id: string;
  mandant_label: string | null;
  readiness_class: GtmReadinessClass;
  readiness_label_de: string;
  primary_segment_label_de: string | null;
  open_points_count: number;
  open_points_hoch: number;
  top_gap_pillar_code: string;
  top_gap_pillar_label_de: string;
  pillar_traffic: Record<BoardReadinessPillarKey, BoardReadinessTraffic>;
  board_report_stale: boolean;
  api_fetch_ok: boolean;
  attention_score: number;
  attention_flags_de: string[];
  last_mandant_readiness_export_at: string | null;
  last_datev_bundle_export_at: string | null;
  last_any_export_at: string | null;
  last_review_marked_at: string | null;
  last_review_note_de: string | null;
  review_stale: boolean;
  any_export_stale: boolean;
  never_any_export: boolean;
  gaps_heavy_without_recent_export: boolean;
  links: {
    mandant_export_page: string;
    datev_bundle_api: string;
    readiness_export_api: string;
    board_readiness_admin: string;
  };
};

/** Wave 41 – priorisierte Arbeitsliste (kein Task-Backend). */
export type KanzleiAttentionQueueItem = {
  tenant_id: string;
  mandant_label: string | null;
  attention_score: number;
  warum_jetzt_de: string[];
  naechster_schritt_de: string;
  links: KanzleiPortfolioRow["links"];
};

export type KanzleiPortfolioPayload = {
  version: typeof KANZLEI_PORTFOLIO_VERSION;
  generated_at: string;
  backend_reachable: boolean;
  mapped_tenant_count: number;
  tenants_partial: number;
  constants: {
    review_stale_days: number;
    any_export_max_age_days: number;
    many_open_points_threshold: number;
    gap_heavy_min_open_for_export_rule: number;
  };
  rows: KanzleiPortfolioRow[];
  attention_queue: KanzleiAttentionQueueItem[];
};

export const KANZLEI_PILLAR_LABEL_DE: Record<string, string> = {
  EU_AI_Act: "EU AI Act",
  ISO_42001: "ISO 42001",
  NIS2: "NIS2",
  DSGVO: "DSGVO",
  none: "—",
};

/** API-Antwort Einzelmandant (Wave 40). */
export type AdvisorMandantHistoryApiDto = {
  tenant_id: string;
  last_mandant_readiness_export_at: string | null;
  last_datev_bundle_export_at: string | null;
  last_any_export_at: string | null;
  last_review_marked_at: string | null;
  last_review_note_de: string | null;
  review_stale: boolean;
  any_export_stale: boolean;
  never_any_export: boolean;
  constants: {
    review_stale_days: number;
    any_export_max_age_days: number;
  };
};
