import { describe, expect, it } from "vitest";

import { stubAdvisorAiGovernancePortfolioDto } from "@/lib/advisorAiGovernanceBuild";
import { buildPartnerReviewPackage } from "@/lib/partnerReviewPackageBuild";
import { partnerReviewPackageMarkdownDe } from "@/lib/partnerReviewPackageMarkdown";
import { stubAdvisorSlaEvaluation } from "@/lib/advisorSlaEvaluate";
import { ADVISOR_SLA_VERSION } from "@/lib/advisorSlaTypes";
import type { KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import { KANZLEI_PORTFOLIO_VERSION } from "@/lib/kanzleiPortfolioTypes";
import { rowToBaselineTenant } from "@/lib/kanzleiMonthlyReportBuild";

function baseRow(partial: Partial<KanzleiPortfolioRow>): KanzleiPortfolioRow {
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

function mkPayload(rows: KanzleiPortfolioRow[]): KanzleiPortfolioPayload {
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
      warum_jetzt_de: ["Review fällig"],
      naechster_schritt_de: "Review durchführen",
      links: r.links,
    })),
    open_reminders: [],
    reminders_due_today_or_overdue_count: 0,
    reminders_due_this_week_open_count: 0,
    advisor_sla: stubAdvisorSlaEvaluation("2026-04-01T12:00:00Z"),
  };
}

describe("partnerReviewPackageBuild", () => {
  it("builds Part A with reminder counts from payload", () => {
    const p = mkPayload([baseRow({ tenant_id: "a", review_stale: true })]);
    p.open_reminders = [
      {
        reminder_id: "r1",
        tenant_id: "a",
        mandant_label: "Acme",
        category: "manual",
        due_at: "2026-04-02T12:00:00Z",
        note: null,
        source: "manual",
      },
    ];
    p.reminders_due_today_or_overdue_count = 1;
    p.reminders_due_this_week_open_count = 1;
    const pkg = buildPartnerReviewPackage(p, null, {
      compareToBaseline: false,
      attentionTopN: 5,
      aiGovernance: stubAdvisorAiGovernancePortfolioDto(p.generated_at),
    });
    expect(pkg.part_e_advisor_kpis).toBeNull();
    expect(pkg.part_f_kpi_trends).toBeNull();
    expect(pkg.part_g_sla_lagebild.version).toBe(ADVISOR_SLA_VERSION);
    expect(pkg.part_a_portfolio_overview.count_review_stale).toBe(1);
    expect(pkg.part_a_portfolio_overview.open_reminders_open_count).toBe(1);
    expect(pkg.part_b_top_attention.length).toBe(1);
  });

  it("merges baseline changes into Part C when compare enabled", () => {
    const cur = baseRow({
      tenant_id: "x",
      readiness_class: "advanced_governance",
      readiness_label_de: "Advanced",
    });
    const base = rowToBaselineTenant(baseRow({ tenant_id: "x", readiness_class: "early_pilot" }));
    const p = mkPayload([cur]);
    const pkg = buildPartnerReviewPackage(
      p,
      { saved_at: "2026-03-01T00:00:00Z", period_label: "2026-03", tenants: { x: base } },
      {
        compareToBaseline: true,
        attentionTopN: 3,
        aiGovernance: stubAdvisorAiGovernancePortfolioDto(p.generated_at),
      },
    );
    expect(pkg.meta.compared_to_baseline).toBe(true);
    expect(pkg.part_c_changes_since_baseline.improvements.length).toBeGreaterThanOrEqual(1);
  });

  it("markdown contains section headers", () => {
    const p = mkPayload([baseRow({})]);
    const pkg = buildPartnerReviewPackage(p, null, {
      compareToBaseline: false,
      attentionTopN: 3,
      aiGovernance: stubAdvisorAiGovernancePortfolioDto(p.generated_at),
    });
    const md = partnerReviewPackageMarkdownDe(pkg);
    expect(md).toContain("## A) Portfolio-Überblick");
    expect(md).toContain("## D) Empfohlene Berater-Prioritäten");
    expect(md).toContain("## G) SLA-Lagebild (Wave 47)");
    expect(md).toContain(`Schema ${ADVISOR_SLA_VERSION}`);
    expect(md).toContain("Portfolio kritisch (mehrere SLA-Critical)");
    expect(md).toContain("Keine SLA-Abweichungen – bestehende Kadenz beibehalten.");
    expect(md).toContain("## H) AI-Governance-Steuerung (Wave 48)");
    expect(md).toContain("## I) Cross-Regulation-Matrix (Wave 49)");
    expect(md).toContain("wave49-v1");
  });
});
