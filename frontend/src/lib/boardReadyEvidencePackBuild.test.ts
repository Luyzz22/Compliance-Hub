import { describe, expect, it } from "vitest";

import { stubAdvisorAiGovernancePortfolioDto } from "@/lib/advisorAiGovernanceBuild";
import { buildAdvisorEvidenceHooksPortfolioDto } from "@/lib/advisorEvidenceHookBuild";
import { buildCrossRegulationMatrixFromPayload } from "@/lib/advisorCrossRegulationBuild";
import { buildBoardReadyEvidencePack } from "@/lib/boardReadyEvidencePackBuild";
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
    open_points_count: 2,
    open_points_hoch: 0,
    top_gap_pillar_code: "DSGVO",
    top_gap_pillar_label_de: "DSGVO",
    pillar_traffic: {
      eu_ai_act: "green",
      iso_42001: "amber",
      nis2: "green",
      dsgvo: "green",
    },
    board_report_stale: false,
    api_fetch_ok: true,
    attention_score: 40,
    attention_flags_de: [],
    last_mandant_readiness_export_at: null,
    last_datev_bundle_export_at: null,
    last_any_export_at: null,
    last_review_marked_at: null,
    last_review_note_de: null,
    review_stale: true,
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
    generated_at: "2026-04-10T10:00:00.000Z",
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
      warum_jetzt_de: ["Review offen"],
      naechster_schritt_de: "Kanzlei-Review terminieren",
      links: r.links,
    })),
    open_reminders: [],
    reminders_due_today_or_overdue_count: 0,
    reminders_due_this_week_open_count: 0,
    advisor_sla: stubAdvisorSlaEvaluation("2026-04-10T10:00:00.000Z"),
  };
}

describe("boardReadyEvidencePackBuild", () => {
  it("builds pack with sections A–E and markdown", () => {
    const p = mkPayload([row({ tenant_id: "a" })]);
    const cr = buildCrossRegulationMatrixFromPayload(p);
    const ag = stubAdvisorAiGovernancePortfolioDto(p.generated_at);
    const eh = buildAdvisorEvidenceHooksPortfolioDto(p, [], {
      generatedAt: new Date("2026-04-10T12:00:00.000Z"),
    });
    const dto = buildBoardReadyEvidencePack({
      payload: p,
      crossRegulation: cr,
      aiGovernance: ag,
      evidenceHooks: eh,
      kpiSnapshot: null,
      generatedAt: new Date("2026-04-10T12:00:00.000Z"),
    });
    expect(dto.meta.version).toBe("wave51-v1");
    expect(dto.meta.included_signals_de.length).toBeGreaterThanOrEqual(5);
    expect(dto.section_a_executive_snapshot.overall_posture_de).toContain("Mandanten");
    expect(dto.section_b_cross_regulation.highlights).toHaveLength(4);
    expect(dto.section_e_next_actions.actions_de.length).toBeGreaterThanOrEqual(3);
    expect(dto.markdown_de).toContain("# Board-Ready Evidence Pack");
    expect(dto.markdown_de).toContain("## A) Executive Readiness Snapshot");
    expect(dto.markdown_de).toContain("## E) Empfohlene Management-Schritte");
    expect(dto.markdown_de).toContain("Eingeschlossene Signalquellen");
  });
});
