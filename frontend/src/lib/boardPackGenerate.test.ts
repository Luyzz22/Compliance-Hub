import { describe, expect, it } from "vitest";

import {
  attentionPriorityScore,
  generateQuarterlyBoardPack,
  inferPillarFromAttention,
  sortAttentionForBoardPack,
} from "@/lib/boardPackGenerate";
import type { BoardAttentionItem } from "@/lib/boardReadinessTypes";

function att(partial: Partial<BoardAttentionItem> & Pick<BoardAttentionItem, "id">): BoardAttentionItem {
  return {
    severity: "amber",
    tenant_id: "t1",
    subject_type: "ai_system",
    missing_artefact_de: "x",
    deep_links: {},
    ...partial,
  };
}

describe("boardPackGenerate", () => {
  it("ranks missing owner above board report at same severity", () => {
    const owner = att({
      id: "1",
      severity: "red",
      missing_artefact_de: "Verantwortlicher fehlt",
    });
    const board = att({
      id: "2",
      severity: "red",
      missing_artefact_de: "Board-Report fehlt",
    });
    expect(attentionPriorityScore(owner)).toBeLessThan(attentionPriorityScore(board));
  });

  it("sorts red before amber", () => {
    const a = att({ id: "a", severity: "amber", missing_artefact_de: "Board-Report fehlt" });
    const r = att({ id: "r", severity: "red", missing_artefact_de: "Sonstiges" });
    const s = sortAttentionForBoardPack([a, r]);
    expect(s[0].id).toBe("r");
  });

  it("infers portfolio pillar for GTM-style items", () => {
    const it = att({
      id: "g",
      tenant_id: "_portfolio",
      missing_artefact_de: "Hohe Nachfrage",
    });
    expect(inferPillarFromAttention(it)).toBe("portfolio");
  });

  it("generates pack with memo, attention, actions and markdown", () => {
    const payload = {
      generated_at: "2026-06-01T10:00:00.000Z",
      backend_reachable: true,
      mapped_tenant_count: 1,
      tenants_partial: 0,
      overall: { status: "amber" as const, label_de: "OK" },
      pillars: [
        {
          pillar: "eu_ai_act" as const,
          title_de: "EU",
          summary_de: "S.",
          status: "green" as const,
          indicators: [],
        },
        {
          pillar: "iso_42001" as const,
          title_de: "ISO",
          summary_de: "S.",
          status: "green" as const,
          indicators: [],
        },
        {
          pillar: "nis2" as const,
          title_de: "N",
          summary_de: "S.",
          status: "green" as const,
          indicators: [],
        },
        {
          pillar: "dsgvo" as const,
          title_de: "D",
          summary_de: "S.",
          status: "green" as const,
          indicators: [],
        },
      ],
      segment_rollups: [],
      readiness_class_rollups: [],
      attention_items: [
        att({
          id: "x1",
          severity: "red",
          subject_id: "sys-1",
          missing_artefact_de: "Verantwortlicher fehlt",
        }),
      ],
      gtm_demand_strip: null,
      notes_de: [],
    };
    const pack = generateQuarterlyBoardPack(payload, null);
    expect(pack.memo.pillar_headlines_de.length).toBe(4);
    expect(pack.attention.length).toBeGreaterThanOrEqual(1);
    expect(pack.actions.length).toBeGreaterThanOrEqual(1);
    expect(pack.markdown_de).toContain("Quarterly Board Pack");
    expect(pack.markdown_de).toContain("Teil C");
  });
});
