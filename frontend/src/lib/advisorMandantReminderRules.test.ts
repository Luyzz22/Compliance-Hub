import { describe, expect, it } from "vitest";

import {
  autoReminderHighGapActive,
  autoReminderPortfolioAttentionActive,
  autoReminderStaleExportActive,
  autoReminderStaleReviewActive,
  defaultAutoDueAtIso,
  isAutoReminderConditionActive,
} from "@/lib/advisorMandantReminderRules";
import type { KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";

function row(p: Partial<KanzleiPortfolioRow>): KanzleiPortfolioRow {
  return {
    tenant_id: "t",
    mandant_label: null,
    readiness_class: "baseline_governance",
    readiness_label_de: "Baseline",
    primary_segment_label_de: null,
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
    ...p,
  };
}

describe("advisorMandantReminderRules", () => {
  it("defaultAutoDueAtIso returns ISO string", () => {
    const iso = defaultAutoDueAtIso(Date.parse("2026-04-08T12:00:00Z"));
    expect(iso).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it("stale review and export flags", () => {
    expect(autoReminderStaleReviewActive(row({ review_stale: true }))).toBe(true);
    expect(autoReminderStaleExportActive(row({ any_export_stale: true }))).toBe(true);
    expect(autoReminderStaleExportActive(row({ never_any_export: true }))).toBe(true);
  });

  it("high gap uses threshold or hoch count", () => {
    expect(autoReminderHighGapActive(row({ open_points_count: 4 }), 4)).toBe(true);
    expect(autoReminderHighGapActive(row({ open_points_hoch: 2 }), 99)).toBe(true);
  });

  it("portfolio attention follows queue qualification", () => {
    expect(
      autoReminderPortfolioAttentionActive(row({ review_stale: true, attention_score: 30 }), 4),
    ).toBe(true);
  });

  it("isAutoReminderConditionActive maps categories", () => {
    const r = row({ review_stale: true });
    expect(isAutoReminderConditionActive(r, "stale_review", 4)).toBe(true);
    expect(isAutoReminderConditionActive(r, "stale_export", 4)).toBe(false);
  });
});
