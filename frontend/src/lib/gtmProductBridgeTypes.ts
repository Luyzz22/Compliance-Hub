import type { GtmReadinessClass } from "@/lib/gtmAccountReadiness";
import type { GtmSegmentBucket } from "@/lib/gtmDashboardTypes";

export type GtmProductBridgeSegmentOverlayRow = {
  segment: GtmSegmentBucket;
  label_de: string;
  inquiries_30d: number;
  qualified_30d: number;
  pipedrive_deals_created_30d: number;
  dominant_readiness: GtmReadinessClass;
  readiness_breakdown: Record<GtmReadinessClass, number>;
};

export type GtmProductBridgePayload = {
  generated_at: string;
  window_days: number;
  map_entry_count: number;
  mapped_tenant_count: number;
  backend_reachable: boolean;
  note_de: string;
  matrix: {
    rows: GtmReadinessClass[];
    columns: GtmSegmentBucket[];
    column_labels_de: Record<GtmSegmentBucket, string>;
    cells: Record<GtmReadinessClass, Record<GtmSegmentBucket, number>>;
    row_totals: Record<GtmReadinessClass, number>;
    column_totals: Record<GtmSegmentBucket, number>;
  };
  segment_overlay: GtmProductBridgeSegmentOverlayRow[];
};

export type GtmProductBridgeHint = {
  mapped: boolean;
  tenant_id: string | null;
  map_label: string | null;
  pilot_flag: boolean;
  readiness_class: GtmReadinessClass;
  readiness_label_de: string;
  governance_hints_de: string[];
  backend_reachable: boolean;
};
