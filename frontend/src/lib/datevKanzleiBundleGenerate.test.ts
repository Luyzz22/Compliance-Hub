import { describe, expect, it } from "vitest";

import {
  buildDatevKanzleiBundleFiles,
  buildNachweisReferenzenRows,
  buildOffenePunkteCsv,
  csvCellSemicolon,
  pillarCodeForOpenPoint,
} from "@/lib/datevKanzleiBundleGenerate";
import { computeMandantOffenePunkte } from "@/lib/tenantBoardReadinessGaps";
import type { TenantBoardReadinessRaw } from "@/lib/tenantBoardReadinessRawTypes";

function minimalRaw(tenantId: string): TenantBoardReadinessRaw {
  return {
    tenant_id: tenantId,
    fetch_ok: true,
    ai_systems: [
      { id: "s1", name: "Bot", owner_email: "owner@example.com", updated_at_utc: "2026-01-01T00:00:00Z" },
    ],
    compliance_by_system: {
      s1: [{ requirement_id: "art9_risk_management", status: "open" }],
    },
    ai_act_doc_items_by_system: { s1: [] },
    compliance_dashboard: {
      tenant_id: tenantId,
      systems: [{ ai_system_id: "s1", ai_system_name: "Bot", risk_level: "high_risk", readiness_score: 0.5 }],
    },
    eu_ai_act_readiness: {
      tenant_id: tenantId,
      overall_readiness: 0.7,
      high_risk_systems_essential_complete: 0,
      high_risk_systems_essential_incomplete: 1,
    },
    ai_compliance_overview: {
      tenant_id: tenantId,
      nis2_kritis_kpi_mean_percent: 42,
    },
    setup_status: { tenant_id: tenantId },
    ai_governance_setup: {},
    board_reports: [{ id: "r1", title: "Q1 Report", created_at: "2026-01-15T12:00:00Z" }],
    ai_act_docs_errors: {},
  };
}

describe("datevKanzleiBundleGenerate", () => {
  it("escapes semicolons and quotes in CSV cells", () => {
    expect(csvCellSemicolon('a;b')).toBe('"a;b"');
    expect(csvCellSemicolon('say "hi"')).toBe('"say ""hi"""');
  });

  it("maps pillars for open points", () => {
    const pBoard = {
      id: "board:t1",
      dringlichkeit: "hoch" as const,
      pruefpunkt_de: "Bericht alt",
      referenz_id: "TENANT-t1",
    };
    expect(pillarCodeForOpenPoint(pBoard)).toBe("EU_AI_Act");
  });

  it("builds open-items CSV with header and UTF-8 BOM", () => {
    const raw = minimalRaw("t-x");
    const nowMs = Date.parse("2026-04-01T00:00:00Z");
    const punkte = computeMandantOffenePunkte("t-x", raw, nowMs);
    const csv = buildOffenePunkteCsv("t-x", raw, punkte);
    expect(csv.charCodeAt(0)).toBe(0xfeff);
    expect(csv).toContain("mandant_id;pillar;object_type");
    expect(csv).toContain("t-x;");
    expect(csv).toMatch(/Risikomanagement|Nachweis/);
  });

  it("builds evidence rows for board, eu aggregate, hr system, nis2", () => {
    const raw = minimalRaw("t-y");
    const nowMs = Date.parse("2026-04-01T00:00:00Z");
    const rows = buildNachweisReferenzenRows("t-y", raw, nowMs);
    const types = rows.map((r) => r.type);
    expect(types).toContain("board_report");
    expect(types).toContain("risk_readiness_aggregate");
    expect(types).toContain("ai_system");
    expect(types).toContain("nis2_kpi_snapshot");
  });

  it("assembles bundle file map with four stable keys", () => {
    const raw = minimalRaw("t-z");
    const nowMs = Date.parse("2026-04-01T00:00:00Z");
    const punkte = computeMandantOffenePunkte("t-z", raw, nowMs);
    const files = buildDatevKanzleiBundleFiles({
      mandantReadinessMarkdownDe: "# Test\n",
      mandantId: "t-z",
      raw,
      punkte,
      nowMs,
      exportPayloadVersion: "wave37-v1",
      generatedAtIso: new Date(nowMs).toISOString(),
    });
    expect(Object.keys(files).sort()).toEqual([
      "01-mandantenstatus.md",
      "02-offene-punkte.csv",
      "03-nachweis-referenzen.csv",
      "04-metadata.json",
    ]);
    expect(files["01-mandantenstatus.md"]).toContain("# Test");
    expect(files["04-metadata.json"]).toContain("wave38-v1");
  });
});
