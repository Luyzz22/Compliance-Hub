import { describe, expect, it } from "vitest";

import {
  ADVISOR_KPI_TRENDS_VERSION,
  buildAdvisorKpiTrendsDto,
  buildKpiTrendNarrativeLinesDe,
} from "@/lib/advisorKpiTrendsBuild";
import type { AdvisorKpiHistoryPoint } from "@/lib/advisorKpiHistoryTypes";

function point(
  day: string,
  review: number,
  exportFresh: number,
  openRem: number,
  noRed: number,
  med: number | null,
): AdvisorKpiHistoryPoint {
  return {
    captured_at: `${day}T12:00:00.000Z`,
    mapped_tenant_count: 10,
    kpi_window_days: 90,
    review_current_share: review,
    export_fresh_share: exportFresh,
    open_reminders_open_count: openRem,
    share_no_open_reminders: 0.5,
    share_no_red_pillar: noRed,
    reminder_median_resolution_hours: med,
  };
}

describe("advisorKpiTrendsBuild", () => {
  it("builds series and direction for review coverage", () => {
    const nowMs = Date.parse("2026-04-10T12:00:00Z");
    const dto = buildAdvisorKpiTrendsDto({
      history: [
        point("2026-04-01", 0.5, 0.5, 3, 0.8, 10),
        point("2026-04-08", 0.7, 0.5, 3, 0.8, 10),
      ],
      period: "4w",
      nowMs,
    });
    expect(dto.version).toBe(ADVISOR_KPI_TRENDS_VERSION);
    const m = dto.metrics.find((x) => x.id === "review_coverage");
    expect(m?.current_value).toBe(0.7);
    expect(m?.previous_value).toBe(0.5);
    expect(m?.direction).toBe("up");
  });

  it("segment filter adds note", () => {
    const dto = buildAdvisorKpiTrendsDto({
      history: [],
      period: "3m",
      nowMs: Date.now(),
      segment_filter: "early_pilot",
    });
    expect(dto.segment_note_de).toContain("portfolio-weit");
  });

  it("narrative mentions open reminders increase", () => {
    const metrics = buildAdvisorKpiTrendsDto({
      history: [
        point("2026-04-01", 0.8, 0.8, 2, 0.9, 5),
        point("2026-04-09", 0.8, 0.8, 6, 0.9, 5),
      ],
      period: "4w",
      nowMs: Date.parse("2026-04-10T12:00:00Z"),
    }).metrics;
    const lines = buildKpiTrendNarrativeLinesDe(metrics);
    expect(lines.some((l) => l.includes("Reminder zugenommen"))).toBe(true);
  });
});
