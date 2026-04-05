import { describe, expect, it } from "vitest";

import { buildKanzleiMonthlyReport } from "@/lib/kanzleiMonthlyReportBuild";
import { kanzleiMonthlyReportMarkdownDe } from "@/lib/kanzleiMonthlyReportMarkdown";
import type { KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import { KANZLEI_PORTFOLIO_VERSION } from "@/lib/kanzleiPortfolioTypes";

function minimalPayload(): KanzleiPortfolioPayload {
  const row: KanzleiPortfolioRow = {
    tenant_id: "t-1",
    mandant_label: null,
    readiness_class: "early_pilot",
    readiness_label_de: "Pilot",
    primary_segment_label_de: null,
    open_points_count: 0,
    open_points_hoch: 0,
    top_gap_pillar_code: "NIS2",
    top_gap_pillar_label_de: "NIS2",
    pillar_traffic: {
      eu_ai_act: "green",
      iso_42001: "green",
      nis2: "amber",
      dsgvo: "green",
    },
    board_report_stale: false,
    api_fetch_ok: true,
    attention_score: 0,
    attention_flags_de: [],
    last_mandant_readiness_export_at: null,
    last_datev_bundle_export_at: null,
    last_any_export_at: null,
    last_review_marked_at: null,
    last_review_note_de: null,
    review_stale: false,
    any_export_stale: false,
    never_any_export: false,
    gaps_heavy_without_recent_export: false,
    open_reminders_count: 0,
    next_reminder_due_at: null,
    links: {
      mandant_export_page: "/a",
      datev_bundle_api: "/b",
      readiness_export_api: "/c",
      board_readiness_admin: "/d",
    },
  };
  return {
    version: KANZLEI_PORTFOLIO_VERSION,
    generated_at: "2026-04-04T10:00:00Z",
    backend_reachable: true,
    mapped_tenant_count: 1,
    tenants_partial: 0,
    constants: {
      review_stale_days: 90,
      any_export_max_age_days: 90,
      many_open_points_threshold: 4,
      gap_heavy_min_open_for_export_rule: 5,
    },
    rows: [row],
    attention_queue: [],
    open_reminders: [],
    reminders_due_today_or_overdue_count: 0,
    reminders_due_this_week_open_count: 0,
  };
}

describe("kanzleiMonthlyReportMarkdown", () => {
  it("includes section headings", () => {
    const p = minimalPayload();
    const r = buildKanzleiMonthlyReport(p, null, {
      periodLabel: "2026-04",
      compareToBaseline: true,
      attentionTopN: 5,
    });
    const md = kanzleiMonthlyReportMarkdownDe(r);
    expect(md).toContain("# Kanzlei-Portfolio-Report");
    expect(md).toContain("## 1) Portfolio-Überblick");
    expect(md).toContain("## 4) Empfohlene Schwerpunkte");
  });
});
