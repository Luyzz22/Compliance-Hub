import { describe, expect, it } from "vitest";

import { buildAdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiPortfolioBuild";
import type { MandantReminderRecord } from "@/lib/advisorMandantReminderTypes";
import type { KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import { KANZLEI_PORTFOLIO_VERSION } from "@/lib/kanzleiPortfolioTypes";

function row(partial: Partial<KanzleiPortfolioRow> = {}): KanzleiPortfolioRow {
  return {
    tenant_id: "t-1",
    mandant_label: "Acme",
    readiness_class: "baseline_governance",
    readiness_label_de: "Baseline",
    primary_segment_label_de: "Kanzlei / WP",
    open_points_count: 0,
    open_points_hoch: 0,
    top_gap_pillar_code: "DSGVO",
    top_gap_pillar_label_de: "DSGVO",
    pillar_traffic: {
      eu_ai_act: "green",
      iso_42001: "green",
      nis2: "green",
      dsgvo: "green",
    },
    board_report_stale: false,
    api_fetch_ok: true,
    attention_score: 2,
    attention_flags_de: [],
    last_mandant_readiness_export_at: "2026-04-01T10:00:00Z",
    last_datev_bundle_export_at: null,
    last_any_export_at: "2026-04-01T10:00:00Z",
    last_review_marked_at: "2026-04-01T10:00:00Z",
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
    ...partial,
  };
}

function payload(rows: KanzleiPortfolioRow[]): KanzleiPortfolioPayload {
  return {
    version: KANZLEI_PORTFOLIO_VERSION,
    generated_at: "2026-04-10T12:00:00Z",
    backend_reachable: true,
    mapped_tenant_count: rows.length,
    tenants_partial: 0,
    constants: {
      review_stale_days: 90,
      any_export_max_age_days: 90,
      many_open_points_threshold: 4,
      gap_heavy_min_open_for_export_rule: 5,
    },
    rows,
    attention_queue: [],
    open_reminders: [],
    reminders_due_today_or_overdue_count: 0,
    reminders_due_this_week_open_count: 0,
  };
}

describe("advisorKpiPortfolioBuild", () => {
  it("computes strip and review share", () => {
    const nowMs = Date.parse("2026-04-10T12:00:00Z");
    const kpi = buildAdvisorKpiPortfolioSnapshot({
      payload: payload([row(), row({ tenant_id: "t-2", review_stale: true })]),
      reminders: [],
      nowMs,
      windowDays: 30,
      segmentBy: "readiness",
    });
    expect(kpi.version).toBe("wave45-v1");
    expect(kpi.review.current_share).toBe(0.5);
    expect(kpi.strip.length).toBe(5);
    expect(kpi.segments.length).toBeGreaterThanOrEqual(1);
  });

  it("median reminder resolution from closed reminders in window", () => {
    const nowMs = Date.parse("2026-04-10T12:00:00Z");
    const closed: MandantReminderRecord = {
      reminder_id: "r1",
      tenant_id: "t-1",
      category: "manual",
      due_at: "2026-04-09T12:00:00Z",
      status: "done",
      note: null,
      source: "manual",
      created_at: "2026-04-09T10:00:00Z",
      updated_at: "2026-04-09T14:00:00Z",
    };
    const kpi = buildAdvisorKpiPortfolioSnapshot({
      payload: payload([row()]),
      reminders: [closed],
      nowMs,
      windowDays: 90,
    });
    expect(kpi.responsiveness.reminder_median_resolution_hours).toBe(4);
    expect(kpi.responsiveness.closed_reminders_in_window).toBe(1);
  });
});
