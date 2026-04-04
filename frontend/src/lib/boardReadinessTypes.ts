/**
 * Wave 34 – Board Readiness Dashboard (internal).
 * Aligns conceptually with `app/board_readiness_models.py`.
 */

export type BoardReadinessTraffic = "green" | "amber" | "red";

export type BoardReadinessPillarKey = "eu_ai_act" | "iso_42001" | "nis2" | "dsgvo";

export type BoardReadinessSubIndicator = {
  key: string;
  label_de: string;
  value_percent: number | null;
  value_count: number | null;
  value_denominator: number | null;
  status: BoardReadinessTraffic;
  source_api_paths: string[];
};

export type BoardReadinessPillarBlock = {
  pillar: BoardReadinessPillarKey;
  title_de: string;
  summary_de: string;
  status: BoardReadinessTraffic;
  indicators: BoardReadinessSubIndicator[];
};

export type BoardAttentionItem = {
  id: string;
  severity: BoardReadinessTraffic;
  tenant_id: string;
  tenant_label?: string | null;
  segment_tag?: string | null;
  readiness_class?: string | null;
  subject_type: "ai_system" | "tenant";
  subject_id?: string | null;
  subject_name?: string | null;
  missing_artefact_de: string;
  last_change_at?: string | null;
  deep_links: Record<string, string>;
};

export type BoardReadinessSegmentRollupRow = {
  segment: import("@/lib/gtmDashboardTypes").GtmSegmentBucket;
  label_de: string;
  /** Demand proxy from GTM (30d window, same as Wave 33 bridge). */
  inquiries_30d: number;
  qualified_30d: number;
  pillar_status: Record<BoardReadinessPillarKey, BoardReadinessTraffic>;
  /** Mean of numeric sub-indicators where defined (0–100). */
  pillar_score_proxy: Record<BoardReadinessPillarKey, number | null>;
  mapped_tenant_count: number;
};

export type BoardReadinessClassRollupRow = {
  readiness_class: import("@/lib/gtmAccountReadiness").GtmReadinessClass;
  label_de: string;
  tenant_count: number;
  pillar_status: Record<BoardReadinessPillarKey, BoardReadinessTraffic>;
  pillar_score_proxy: Record<BoardReadinessPillarKey, number | null>;
};

export type BoardReadinessGtmDemandStrip = {
  window_days: number;
  segment_rows: Array<{
    segment: import("@/lib/gtmDashboardTypes").GtmSegmentBucket;
    label_de: string;
    inquiries_30d: number;
    qualified_30d: number;
    dominant_readiness: import("@/lib/gtmAccountReadiness").GtmReadinessClass;
  }>;
};

export type BoardReadinessPayload = {
  generated_at: string;
  backend_reachable: boolean;
  mapped_tenant_count: number;
  tenants_partial: number;
  overall: {
    status: BoardReadinessTraffic;
    label_de: string;
  };
  pillars: BoardReadinessPillarBlock[];
  segment_rollups: BoardReadinessSegmentRollupRow[];
  readiness_class_rollups: BoardReadinessClassRollupRow[];
  attention_items: BoardAttentionItem[];
  gtm_demand_strip: BoardReadinessGtmDemandStrip | null;
  notes_de: string[];
};

export type BoardReadinessBanner = BoardReadinessPayload["overall"] & {
  mapped_tenant_count: number;
  backend_reachable: boolean;
};
