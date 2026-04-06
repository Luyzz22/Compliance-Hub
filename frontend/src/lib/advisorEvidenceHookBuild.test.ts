import { describe, expect, it } from "vitest";

import { buildAdvisorEvidenceHooksPortfolioDto, evidenceDomainComplianceRelevanceDe } from "@/lib/advisorEvidenceHookBuild";
import type { EvidenceHookStoredRecord } from "@/lib/advisorEvidenceHookTypes";
import type { KanzleiPortfolioPayload, KanzleiPortfolioRow } from "@/lib/kanzleiPortfolioTypes";
import { KANZLEI_PORTFOLIO_VERSION } from "@/lib/kanzleiPortfolioTypes";
import { stubAdvisorSlaEvaluation } from "@/lib/advisorSlaEvaluate";

const NOW = Date.parse("2026-04-04T12:00:00.000Z");

function baseRow(p: Partial<KanzleiPortfolioRow>): KanzleiPortfolioRow {
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
    ...p,
  };
}

function mkPayload(rows: KanzleiPortfolioRow[]): KanzleiPortfolioPayload {
  return {
    version: KANZLEI_PORTFOLIO_VERSION,
    generated_at: "2026-04-04T10:00:00.000Z",
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
    advisor_sla: stubAdvisorSlaEvaluation("2026-04-04T10:00:00.000Z"),
  };
}

describe("advisorEvidenceHookBuild", () => {
  it("evidenceDomainComplianceRelevanceDe covers invoice and access", () => {
    expect(evidenceDomainComplianceRelevanceDe("invoice").some((s) => s.includes("GoBD"))).toBe(true);
    expect(evidenceDomainComplianceRelevanceDe("access").some((s) => s.includes("NIS2"))).toBe(true);
  });

  it("adds synthetic DATEV and SAP rows when store empty", () => {
    const p = mkPayload([baseRow({ tenant_id: "a" })]);
    const dto = buildAdvisorEvidenceHooksPortfolioDto(p, [], {
      generatedAt: new Date(NOW),
      nowMs: NOW,
    });
    const m = dto.mandanten[0];
    expect(m.hooks.length).toBe(2);
    expect(m.hooks.filter((h) => h.source_system_type === "datev").length).toBe(1);
    expect(m.hooks.filter((h) => h.source_system_type === "sap_s4hana").length).toBe(1);
    expect(dto.summary.mandanten_without_datev_export).toBe(1);
    expect(dto.summary.mandanten_without_sap_touchpoint).toBe(1);
    expect(dto.version).toBe("wave50-v1");
    expect(dto.markdown_de).toContain("Enterprise Evidence Hooks");
  });

  it("DATEV synthetic connected when recent export", () => {
    const p = mkPayload([
      baseRow({
        last_datev_bundle_export_at: "2026-04-01T10:00:00.000Z",
      }),
    ]);
    const dto = buildAdvisorEvidenceHooksPortfolioDto(p, [], { nowMs: NOW });
    const dv = dto.mandanten[0].hooks.find((h) => h.source_system_type === "datev");
    expect(dv?.connection_status).toBe("connected");
  });

  it("skips synthetic SAP when stored SAP planned exists", () => {
    const stored: EvidenceHookStoredRecord[] = [
      {
        hook_id: "h1",
        tenant_id: "t-1",
        source_system_type: "sap_btp",
        source_label: "BTP",
        evidence_domain: "access",
        connection_status: "planned",
        last_sync_at: null,
        note: null,
      },
    ];
    const p = mkPayload([baseRow({})]);
    const dto = buildAdvisorEvidenceHooksPortfolioDto(p, stored, { nowMs: NOW });
    const sapRows = dto.mandanten[0].hooks.filter(
      (h) => h.source_system_type === "sap_s4hana" || h.source_system_type === "sap_btp",
    );
    expect(sapRows.length).toBe(1);
    expect(sapRows[0].is_synthetic).toBe(false);
    expect(dto.summary.mandanten_without_sap_touchpoint).toBe(0);
  });

  it("counts enterprise upsell when governance + pressure signals", () => {
    const p = mkPayload([
      baseRow({
        readiness_class: "advanced_governance",
        open_points_count: 5,
      }),
    ]);
    const dto = buildAdvisorEvidenceHooksPortfolioDto(p, [], { nowMs: NOW });
    expect(dto.summary.mandanten_enterprise_upsell_candidates).toBe(1);
  });
});
