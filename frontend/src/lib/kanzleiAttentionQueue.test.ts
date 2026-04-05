import { describe, expect, it } from "vitest";

import {
  buildAttentionQueue,
  naechsterSchrittForRow,
  rowQualifiesForAttentionQueue,
  warumJetztForRow,
} from "@/lib/kanzleiAttentionQueue";
import type { KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";

const MANY = 4;

function baseRow(over: Partial<KanzleiPortfolioRow> = {}): KanzleiPortfolioRow {
  return {
    tenant_id: "t-1",
    mandant_label: "Acme",
    readiness_class: "baseline_governance",
    readiness_label_de: "Baseline-Governance (Board/KPIs/Inventar)",
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
      mandant_export_page: "/admin/advisor-mandant-export?client_id=t-1",
      datev_bundle_api: "/api/x",
      readiness_export_api: "/api/y",
      board_readiness_admin: "/admin/board-readiness",
    },
    ...over,
  };
}

describe("kanzleiAttentionQueue", () => {
  it("qualifies on review stale", () => {
    expect(rowQualifiesForAttentionQueue(baseRow({ attention_score: 24, review_stale: true }), MANY)).toBe(
      true,
    );
  });

  it("does not qualify when quiet", () => {
    expect(rowQualifiesForAttentionQueue(baseRow({ attention_score: 0 }), MANY)).toBe(false);
  });

  it("naechsterSchritt prefers API fix", () => {
    const t = naechsterSchrittForRow(baseRow({ api_fetch_ok: false, review_stale: true }), MANY);
    expect(t).toContain("Zugriff");
  });

  it("naechsterSchritt suggests export when gaps heavy without export", () => {
    const t = naechsterSchrittForRow(
      baseRow({ gaps_heavy_without_recent_export: true, review_stale: true }),
      MANY,
    );
    expect(t.toLowerCase()).toContain("export");
  });

  it("buildAttentionQueue preserves score ordering from input rows", () => {
    const rows = [
      baseRow({ tenant_id: "a", attention_score: 10, review_stale: true }),
      baseRow({ tenant_id: "b", attention_score: 50, any_export_stale: true }),
    ];
    const q = buildAttentionQueue(rows, MANY);
    expect(q[0]?.tenant_id).toBe("b");
  });

  it("warumJetzt lists review when stale", () => {
    const w = warumJetztForRow(baseRow({ review_stale: true, attention_score: 30 }), MANY);
    expect(w.some((x) => x.includes("Review"))).toBe(true);
  });
});
