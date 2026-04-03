import { describe, expect, it } from "vitest";

import { evaluateGtmAlertsFromSnapshot } from "@/lib/gtmAlertEvaluator";
import type { GtmDashboardSnapshot } from "@/lib/gtmDashboardTypes";

function minimalSnapshot(
  counts: Partial<GtmDashboardSnapshot["health_signal_counts"]>,
): GtmDashboardSnapshot {
  const base = {
    untriaged_over_3d: 0,
    stuck_failed_crm_sync_24h: 0,
    qualified_no_pipedrive_deal_old_7d: 0,
    crm_dead_letter_30d: 0,
    crm_failed_30d: 0,
  };
  return {
    generated_at: "2026-04-01T12:00:00.000Z",
    windows: {
      "7d": { start: "", end: "" },
      "30d": { start: "", end: "" },
    },
    kpis: {
      "7d": {} as GtmDashboardSnapshot["kpis"]["7d"],
      "30d": {} as GtmDashboardSnapshot["kpis"]["30d"],
    },
    funnel: [],
    segment_table: [],
    attention: [],
    trends: { inquiries_per_day_utc: [], qualified_and_deals_per_week_utc: [] },
    attribution_by_source_30d: [],
    attribution_by_campaign_30d: [],
    source_volume_by_attribution_7d: [],
    health_signal_counts: { ...base, ...counts },
    health: {
      tiles: [],
      ops_hints: [],
      segment_readiness: [],
      attribution_health_top3: [],
    },
    data_notes: {
      cta_clicks_persisted: false,
      cta_note_de: "",
      funnel_note_de: "",
      attribution_note_de: "",
      health_note_de: "",
    },
  } as unknown as GtmDashboardSnapshot;
}

describe("evaluateGtmAlertsFromSnapshot", () => {
  it("returns empty when all quiet", () => {
    expect(evaluateGtmAlertsFromSnapshot(minimalSnapshot({})).length).toBe(0);
  });

  it("fires critical untriaged", () => {
    const f = evaluateGtmAlertsFromSnapshot(minimalSnapshot({ untriaged_over_3d: 10 }));
    expect(f.some((x) => x.id === "untriaged_backlog_critical")).toBe(true);
  });
});
