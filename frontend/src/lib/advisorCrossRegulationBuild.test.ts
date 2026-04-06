import { describe, expect, it } from "vitest";

import {
  buildCrossRegulationMatrixFromPayload,
  stubCrossRegulationMatrixDto,
  trafficToCrossRegulationBucket,
} from "@/lib/advisorCrossRegulationBuild";
import { ADVISOR_CROSS_REGULATION_VERSION } from "@/lib/advisorCrossRegulationTypes";
import type { KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import { KANZLEI_PORTFOLIO_VERSION } from "@/lib/kanzleiPortfolioTypes";
import { stubAdvisorSlaEvaluation } from "@/lib/advisorSlaEvaluate";

function row(partial: Partial<KanzleiPortfolioRow>): KanzleiPortfolioRow {
  return {
    tenant_id: "t-1",
    mandant_label: "Acme",
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
    attention_score: 5,
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
      mandant_export_page: "/x",
      datev_bundle_api: "/y",
      readiness_export_api: "/z",
      board_readiness_admin: "/b",
    },
    ...partial,
  };
}

function mkPayload(rows: KanzleiPortfolioRow[]): KanzleiPortfolioPayload {
  return {
    version: KANZLEI_PORTFOLIO_VERSION,
    generated_at: "2026-05-01T12:00:00Z",
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
    advisor_sla: stubAdvisorSlaEvaluation("2026-05-01T12:00:00Z"),
  };
}

describe("advisorCrossRegulationBuild", () => {
  it("trafficToCrossRegulationBucket respects api and traffic", () => {
    expect(trafficToCrossRegulationBucket("green", true)).toBe("ok");
    expect(trafficToCrossRegulationBucket("amber", true)).toBe("needs_attention");
    expect(trafficToCrossRegulationBucket("red", true)).toBe("priority");
    expect(trafficToCrossRegulationBucket("green", false)).toBe("unknown");
  });

  it("stubCrossRegulationMatrixDto has version", () => {
    const dto = stubCrossRegulationMatrixDto("2026-05-01T12:00:00Z");
    expect(dto.version).toBe(ADVISOR_CROSS_REGULATION_VERSION);
  });

  it("buildCrossRegulationMatrixFromPayload counts multi-pillar stress", () => {
    const dto = buildCrossRegulationMatrixFromPayload(
      mkPayload([
        row({
          tenant_id: "a",
          pillar_traffic: {
            eu_ai_act: "red",
            iso_42001: "red",
            nis2: "green",
            dsgvo: "green",
          },
        }),
        row({
          tenant_id: "b",
          pillar_traffic: {
            eu_ai_act: "green",
            iso_42001: "green",
            nis2: "green",
            dsgvo: "green",
          },
        }),
      ]),
    );
    expect(dto.totals.mandanten_multi_pillar_priority).toBe(1);
    expect(dto.mandanten.find((m) => m.tenant_id === "a")?.priority_pillar_count).toBe(2);
  });

  it("gap pressure bumps pillar when top_gap matches and open points", () => {
    const dto = buildCrossRegulationMatrixFromPayload(
      mkPayload([
        row({
          pillar_traffic: {
            eu_ai_act: "green",
            iso_42001: "green",
            nis2: "green",
            dsgvo: "green",
          },
          top_gap_pillar_code: "DSGVO",
          open_points_count: 5,
          open_points_hoch: 1,
        }),
      ]),
    );
    const m = dto.mandanten[0]!;
    expect(m.pillars.dsgvo).toBe("needs_attention");
    expect(m.pillars.eu_ai_act).toBe("ok");
  });
});
