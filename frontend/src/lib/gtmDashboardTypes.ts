import type { GtmWindowKey } from "@/lib/gtmDashboardTime";
import type { LeadSyncTarget } from "@/lib/leadSyncTypes";

export type { GtmWindowKey } from "@/lib/gtmDashboardTime";

export type GtmSegmentBucket = "industrie_mittelstand" | "kanzlei_wp" | "enterprise_sap" | "other";

export type GtmWindowMetrics = {
  inbound_inquiries: number;
  repeated_contact_inquiries: number;
  qualified_leads: number;
  contacted_leads: number;
  failed_webhook_forwards: number;
  dead_letter_sync_jobs: number;
  hubspot_synced_jobs: number;
  pipedrive_deals_created: number;
  by_segment: Record<GtmSegmentBucket, { inquiries: number; qualified: number }>;
};

export type GtmFunnelStage = {
  id: string;
  label_de: string;
  counts: Record<GtmWindowKey, number>;
};

export type GtmAttentionItem = {
  kind: string;
  lead_id?: string;
  job_id?: string;
  target?: LeadSyncTarget;
  detail?: string;
  at: string;
};

export type GtmDailyPoint = { day: string; inquiries: number };
export type GtmWeeklyPoint = {
  week_start: string;
  qualified: number;
  pipedrive_deals_created: number;
};

export type GtmAttributionBreakdownRow = {
  key: string;
  label_de: string;
  inquiries_30d: number;
  qualified_30d: number;
  pipedrive_deals_created_30d: number;
};

export type GtmDashboardSnapshot = {
  generated_at: string;
  windows: Record<GtmWindowKey, { start: string; end: string }>;
  kpis: Record<GtmWindowKey, GtmWindowMetrics>;
  funnel: GtmFunnelStage[];
  segment_table: {
    segment: GtmSegmentBucket;
    label_de: string;
    inquiries_30d: number;
    qualified_30d: number;
    sync_issues_30d: number;
  }[];
  attention: GtmAttentionItem[];
  trends: {
    inquiries_per_day_utc: GtmDailyPoint[];
    qualified_and_deals_per_week_utc: GtmWeeklyPoint[];
  };
  /** Wave 30 – letzte 30 Tage, keine Multi-Touch-Modelle */
  attribution_by_source_30d: GtmAttributionBreakdownRow[];
  attribution_by_campaign_30d: GtmAttributionBreakdownRow[];
  data_notes: {
    cta_clicks_persisted: boolean;
    cta_note_de: string;
    funnel_note_de: string;
    attribution_note_de: string;
  };
};
