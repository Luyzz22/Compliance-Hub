import { describe, expect, it } from "vitest";

import { buildAdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiPortfolioBuild";
import {
  evaluateAdvisorSla,
  resolveAdvisorSlaMetricValue,
  stubAdvisorSlaEvaluation,
} from "@/lib/advisorSlaEvaluate";
import type { KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import { KANZLEI_PORTFOLIO_VERSION } from "@/lib/kanzleiPortfolioTypes";

function baseRow(partial: Partial<KanzleiPortfolioRow> = {}): KanzleiPortfolioRow {
  return {
    tenant_id: "t-1",
    mandant_label: "A",
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
    ...partial,
  };
}

function mkPayload(over: Partial<KanzleiPortfolioPayload> = {}): KanzleiPortfolioPayload {
  const rows = over.rows ?? [baseRow()];
  const nowIso = "2026-06-01T12:00:00Z";
  const base: KanzleiPortfolioPayload = {
    version: KANZLEI_PORTFOLIO_VERSION,
    generated_at: nowIso,
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
    advisor_sla: stubAdvisorSlaEvaluation(nowIso),
  };
  return { ...base, ...over, advisor_sla: over.advisor_sla ?? base.advisor_sla };
}

describe("advisorSlaEvaluate", () => {
  it("resolves payload metrics", () => {
    const p = mkPayload({
      attention_queue: [{ tenant_id: "t-1", mandant_label: null, attention_score: 5, warum_jetzt_de: [], naechster_schritt_de: "x", links: baseRow().links }],
    });
    expect(resolveAdvisorSlaMetricValue("payload.attention_queue_size", p, null)).toBe(1);
  });

  it("flags low review coverage from KPI", () => {
    const rows = [baseRow({ tenant_id: "a" }), baseRow({ tenant_id: "b", review_stale: true })];
    const p = mkPayload({ rows, attention_queue: [] });
    const nowMs = Date.parse("2026-06-01T12:00:00Z");
    const kpi = buildAdvisorKpiPortfolioSnapshot({ payload: p, reminders: [], nowMs, windowDays: 90 });
    const dto = evaluateAdvisorSla({
      payload: p,
      kpiSnapshot: kpi,
      nowMs,
      previousCriticalRuleIds: [],
    });
    const warn = dto.findings.find((f) => f.rule_id === "sla_review_coverage_warn");
    expect(warn).toBeDefined();
    expect(warn?.severity).toBe("warning");
  });

  it("portfolio_red when multiple critical findings", () => {
    const rows = Array.from({ length: 5 }, (_, i) =>
      baseRow({ tenant_id: `t-${i}`, never_any_export: true, review_stale: true, pillar_traffic: { eu_ai_act: "red", iso_42001: "green", nis2: "green", dsgvo: "green" } }),
    );
    const queue = rows.slice(0, 5).map((r) => ({
      tenant_id: r.tenant_id,
      mandant_label: r.mandant_label,
      attention_score: 80,
      warum_jetzt_de: ["x"],
      naechster_schritt_de: "y",
      links: r.links,
    }));
    const p = mkPayload({
      rows,
      attention_queue: queue,
      open_reminders: Array.from({ length: 30 }, (_, i) => ({
        reminder_id: `r-${i}`,
        tenant_id: "t-0",
        mandant_label: null,
        category: "manual" as const,
        due_at: "2026-06-02T12:00:00Z",
        note: null,
        source: "manual" as const,
      })),
      reminders_due_today_or_overdue_count: 10,
    });
    const nowMs = Date.parse("2026-06-01T12:00:00Z");
    const kpi = buildAdvisorKpiPortfolioSnapshot({ payload: p, reminders: [], nowMs, windowDays: 90 });
    const dto = evaluateAdvisorSla({
      payload: p,
      kpiSnapshot: kpi,
      nowMs,
      previousCriticalRuleIds: [],
    });
    const crit = dto.findings.filter((f) => f.severity === "critical");
    expect(crit.length).toBeGreaterThanOrEqual(2);
    expect(dto.signals.find((s) => s.signal_id === "portfolio_red")?.active).toBe(true);
  });
});
