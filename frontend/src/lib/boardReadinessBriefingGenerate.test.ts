import { describe, expect, it } from "vitest";

import {
  baselineFromPayload,
  briefingRefIdForAttentionItem,
  buildBriefingMarkdownDe,
  computeDeltaBulletsDe,
  generateBoardReadinessBriefing,
} from "@/lib/boardReadinessBriefingGenerate";
import type { BoardReadinessPayload } from "@/lib/boardReadinessTypes";

function minimalPayload(overrides: Partial<BoardReadinessPayload> = {}): BoardReadinessPayload {
  const base: BoardReadinessPayload = {
    generated_at: "2026-04-01T12:00:00.000Z",
    backend_reachable: true,
    mapped_tenant_count: 2,
    tenants_partial: 0,
    overall: { status: "amber", label_de: "Test" },
    pillars: [
      {
        pillar: "eu_ai_act",
        title_de: "EU AI Act",
        summary_de: "s",
        status: "amber",
        indicators: [
          {
            key: "k1",
            label_de: "Indikator 1",
            value_percent: 50,
            value_count: 1,
            value_denominator: 2,
            status: "amber",
            source_api_paths: ["/x"],
          },
        ],
      },
      {
        pillar: "iso_42001",
        title_de: "ISO 42001",
        summary_de: "s",
        status: "green",
        indicators: [],
      },
      {
        pillar: "nis2",
        title_de: "NIS2",
        summary_de: "s",
        status: "green",
        indicators: [],
      },
      {
        pillar: "dsgvo",
        title_de: "DSGVO",
        summary_de: "s",
        status: "green",
        indicators: [],
      },
    ],
    segment_rollups: [],
    readiness_class_rollups: [],
    attention_items: [
      {
        id: "a1",
        severity: "red",
        tenant_id: "t-acme",
        tenant_label: "ACME EU",
        subject_type: "ai_system",
        subject_id: "sys-1",
        subject_name: "Credit Bot",
        missing_artefact_de: "Board-Report fehlt",
        deep_links: {},
      },
    ],
    gtm_demand_strip: {
      window_days: 30,
      segment_rows: [
        {
          segment: "industrie_mittelstand",
          label_de: "Mittelstand",
          inquiries_30d: 10,
          qualified_30d: 4,
          dominant_readiness: "early_pilot",
        },
      ],
    },
    notes_de: [],
  };
  return { ...base, ...overrides };
}

describe("boardReadinessBriefingGenerate", () => {
  it("formats HR-AI ref for ai_system attention items", () => {
    expect(
      briefingRefIdForAttentionItem({
        id: "x",
        severity: "red",
        tenant_id: "t1",
        subject_type: "ai_system",
        subject_id: "my-sys",
        missing_artefact_de: "m",
        deep_links: {},
      }),
    ).toBe("HR-AI-my-sys");
  });

  it("formats TENANT ref for tenant-level items", () => {
    expect(
      briefingRefIdForAttentionItem({
        id: "x",
        severity: "amber",
        tenant_id: "tenant-acme",
        subject_type: "tenant",
        missing_artefact_de: "m",
        deep_links: {},
      }),
    ).toBe("TENANT-tenant-acme");
  });

  it("computes deltas when baseline differs", () => {
    const cur = minimalPayload({
      overall: { status: "red", label_de: "X" },
    });
    const baseline = baselineFromPayload(minimalPayload());
    const bullets = computeDeltaBulletsDe(cur, baseline);
    expect(bullets.some((b) => b.includes("Portfolio-Ampel"))).toBe(true);
  });

  it("generates briefing with five sections and markdown", () => {
    const b = generateBoardReadinessBriefing(minimalPayload(), null);
    expect(b.sections.length).toBe(5);
    expect(b.markdown_de).toContain("# Board Readiness Briefing");
    expect(b.markdown_de).toContain("HR-AI-sys-1");
  });

  it("buildBriefingMarkdownDe includes delta block", () => {
    const md = buildBriefingMarkdownDe(
      "T",
      "2026-01-01T00:00:00.000Z",
      [{ id: "1", heading_de: "H", bullets: ["a"] }],
      ["Delta eins"],
      null,
    );
    expect(md).toContain("Delta eins");
    expect(md).toContain("## H");
  });
});
