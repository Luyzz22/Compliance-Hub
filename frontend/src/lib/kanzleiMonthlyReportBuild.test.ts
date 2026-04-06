import { describe, expect, it } from "vitest";

import { stubAdvisorAiGovernancePortfolioDto } from "@/lib/advisorAiGovernanceBuild";
import { buildAdvisorEvidenceHooksPortfolioDto } from "@/lib/advisorEvidenceHookBuild";
import {
  attentionBand,
  buildKanzleiMonthlyReport,
  rowToBaselineTenant,
  worstPillarTrafficFromRow,
} from "@/lib/kanzleiMonthlyReportBuild";
import { stubAdvisorSlaEvaluation } from "@/lib/advisorSlaEvaluate";
import type { KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import { KANZLEI_PORTFOLIO_VERSION } from "@/lib/kanzleiPortfolioTypes";

function row(partial: Partial<KanzleiPortfolioRow>): KanzleiPortfolioRow {
  return {
    tenant_id: "t-1",
    mandant_label: "Acme",
    readiness_class: "baseline_governance",
    readiness_label_de: "Baseline",
    primary_segment_label_de: null,
    open_points_count: 1,
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

function payload(rows: KanzleiPortfolioRow[]): KanzleiPortfolioPayload {
  return {
    version: KANZLEI_PORTFOLIO_VERSION,
    generated_at: "2026-04-01T12:00:00Z",
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
    attention_queue: rows.map((r) => ({
      tenant_id: r.tenant_id,
      mandant_label: r.mandant_label,
      attention_score: r.attention_score,
      warum_jetzt_de: ["Test"],
      naechster_schritt_de: "Test-Schritt",
      links: r.links,
    })),
    open_reminders: [],
    reminders_due_today_or_overdue_count: 0,
    reminders_due_this_week_open_count: 0,
    advisor_sla: stubAdvisorSlaEvaluation("2026-04-01T12:00:00Z"),
  };
}

function evidenceHooksFor(p: KanzleiPortfolioPayload) {
  return buildAdvisorEvidenceHooksPortfolioDto(p, [], { generatedAt: new Date(p.generated_at) });
}

describe("kanzleiMonthlyReportBuild", () => {
  it("attentionBand buckets scores", () => {
    expect(attentionBand(10)).toBe("low");
    expect(attentionBand(30)).toBe("medium");
    expect(attentionBand(60)).toBe("high");
  });

  it("worstPillarTrafficFromRow returns red if any red", () => {
    expect(worstPillarTrafficFromRow(row({ pillar_traffic: { eu_ai_act: "red", iso_42001: "green", nis2: "green", dsgvo: "green" } }))).toBe("red");
  });

  it("buildKanzleiMonthlyReport detects readiness improvement vs baseline", () => {
    const cur = row({ tenant_id: "x", readiness_class: "advanced_governance", readiness_label_de: "Advanced" });
    const base = rowToBaselineTenant(row({ tenant_id: "x", readiness_class: "early_pilot" }));
    const p = payload([cur]);
    const r = buildKanzleiMonthlyReport(
      p,
      { saved_at: "2026-03-01T00:00:00Z", period_label: "2026-03", tenants: { x: base } },
      {
        periodLabel: "2026-04",
        compareToBaseline: true,
        attentionTopN: 5,
        aiGovernance: stubAdvisorAiGovernancePortfolioDto(p.generated_at),
        evidenceHooks: evidenceHooksFor(p),
      },
    );
    expect(r.compared_to_baseline).toBe(true);
    expect(r.section_3_changes.readiness_improved.length).toBe(1);
    expect(r.section_6_kpi_trends).toBeNull();
  });

  it("buildKanzleiMonthlyReport skips compare when compareToBaseline false", () => {
    const cur = row({ tenant_id: "x" });
    const base = rowToBaselineTenant(row({ tenant_id: "x", open_points_count: 0 }));
    const p = payload([cur]);
    const r = buildKanzleiMonthlyReport(
      p,
      { saved_at: "2026-03-01T00:00:00Z", period_label: "2026-03", tenants: { x: base } },
      {
        periodLabel: "2026-04",
        compareToBaseline: false,
        attentionTopN: 5,
        aiGovernance: stubAdvisorAiGovernancePortfolioDto(p.generated_at),
        evidenceHooks: evidenceHooksFor(p),
      },
    );
    expect(r.compared_to_baseline).toBe(false);
    expect(r.section_3_changes.readiness_improved.length).toBe(0);
    expect(r.section_5_advisor_kpis).toBeNull();
  });
});
