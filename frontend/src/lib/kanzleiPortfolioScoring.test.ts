import { describe, expect, it } from "vitest";

import { kanzleiAttentionScore } from "@/lib/kanzleiPortfolioScoring";

describe("kanzleiPortfolioScoring", () => {
  it("ranks higher attention when board stale and many open points", () => {
    const base = {
      open_points_count: 2,
      open_points_hoch: 0,
      board_report_stale: false,
      any_export_stale: false,
      baseline_gap: false,
      api_fetch_ok: true,
      review_stale: false,
      gaps_heavy_without_recent_export: false,
      pillar_traffic: {
        eu_ai_act: "green" as const,
        iso_42001: "green" as const,
        nis2: "green" as const,
        dsgvo: "green" as const,
      },
    };
    const low = kanzleiAttentionScore(base);
    const high = kanzleiAttentionScore({
      ...base,
      open_points_count: 6,
      open_points_hoch: 2,
      board_report_stale: true,
      any_export_stale: true,
      baseline_gap: true,
      api_fetch_ok: false,
      review_stale: true,
      gaps_heavy_without_recent_export: true,
      pillar_traffic: {
        eu_ai_act: "red",
        iso_42001: "amber",
        nis2: "green",
        dsgvo: "green",
      },
    });
    expect(high).toBeGreaterThan(low);
  });
});
