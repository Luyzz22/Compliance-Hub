import { describe, expect, it } from "vitest";

import { generateMandantReadinessAdvisorExport } from "@/lib/mandantReadinessAdvisorExport";
import type { TenantBoardReadinessRaw } from "@/lib/tenantBoardReadinessRawTypes";

function minimalRaw(tenantId: string): TenantBoardReadinessRaw {
  return {
    tenant_id: tenantId,
    fetch_ok: true,
    ai_systems: [{ id: "s1", name: "Bot", owner_email: "a@b.de" }],
    compliance_by_system: {
      s1: [
        { requirement_id: "art9_risk_management", status: "completed" },
        { requirement_id: "art11_technical_documentation", status: "completed" },
      ],
    },
    ai_act_doc_items_by_system: {},
    compliance_dashboard: {
      tenant_id: tenantId,
      systems: [{ ai_system_id: "s1", ai_system_name: "Bot", risk_level: "high_risk" }],
    },
    eu_ai_act_readiness: {
      tenant_id: tenantId,
      overall_readiness: 0.8,
      high_risk_systems_essential_complete: 1,
      high_risk_systems_essential_incomplete: 0,
    },
    ai_compliance_overview: null,
    setup_status: { tenant_id: tenantId, policies_published: true },
    ai_governance_setup: {
      governance_roles: { dpo: "dpo@x.de" },
      progress_steps: [3, 6],
      active_frameworks: ["iso_42001"],
    },
    board_reports: [{ id: "r1", title: "Q1", created_at: new Date().toISOString() }],
    ai_act_docs_errors: {},
  };
}

describe("mandantReadinessAdvisorExport", () => {
  it("builds markdown with four sections", () => {
    const p = generateMandantReadinessAdvisorExport({
      mandantId: "t-demo",
      mandantenBezeichnung: "Demo GmbH",
      raw: minimalRaw("t-demo"),
      pilotFlag: false,
      nowMs: Date.now(),
    });
    expect(p.markdown_de).toContain("Mandantenstatus – Readiness");
    expect(p.markdown_de).toContain("## 1. Mandantenstatus kompakt");
    expect(p.markdown_de).toContain("## 2. Offene Punkte");
    expect(p.markdown_de).toContain("## 3. Nächste Schritte");
    expect(p.markdown_de).toContain("## 4. Nachweise");
    expect(p.kompakt.mandanten_bezeichnung).toBe("Demo GmbH");
  });
});
