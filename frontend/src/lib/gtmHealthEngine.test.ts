import { describe, expect, it } from "vitest";

import { evaluateGtmHealth } from "@/lib/gtmHealthEngine";

const emptySeg = (
  segment: "industrie_mittelstand" | "kanzlei_wp" | "enterprise_sap" | "other",
  label_de: string,
) => ({
  segment,
  label_de,
  inquiries_30d: 0,
  qualified_30d: 0,
  hubspot_sent_30d: 0,
  pipedrive_touch_30d: 0,
  dominant_sources_de: "—",
});

describe("evaluateGtmHealth", () => {
  it("returns four tiles and empty hints for quiet zero-data input", () => {
    const h = evaluateGtmHealth({
      inbound_30d: 0,
      webhook_failed_30d: 0,
      spam_30d: 0,
      untriaged_over_3d: 0,
      crm_dead_letter_30d: 0,
      crm_failed_30d: 0,
      crm_sent_ok_30d: 0,
      qualified_30d: 0,
      deals_created_30d: 0,
      stuck_failed_crm_sync_24h: 0,
      qualified_no_pipedrive_deal_old_7d: 0,
      segments: [
        emptySeg("industrie_mittelstand", "Industrie"),
        emptySeg("kanzlei_wp", "Kanzlei"),
        emptySeg("enterprise_sap", "Enterprise"),
        emptySeg("other", "Sonstiges"),
      ],
      attribution_top_sources: [],
    });
    expect(h.tiles).toHaveLength(4);
    expect(h.ops_hints.length).toBe(0);
    expect(h.attribution_health_top3).toHaveLength(0);
  });

  it("flags issue when many old untriaged leads", () => {
    const h = evaluateGtmHealth({
      inbound_30d: 10,
      webhook_failed_30d: 0,
      spam_30d: 0,
      untriaged_over_3d: 6,
      crm_dead_letter_30d: 0,
      crm_failed_30d: 0,
      crm_sent_ok_30d: 2,
      qualified_30d: 1,
      deals_created_30d: 0,
      stuck_failed_crm_sync_24h: 0,
      qualified_no_pipedrive_deal_old_7d: 0,
      segments: [
        emptySeg("industrie_mittelstand", "Industrie"),
        emptySeg("kanzlei_wp", "Kanzlei"),
        emptySeg("enterprise_sap", "Enterprise"),
        emptySeg("other", "Sonstiges"),
      ],
      attribution_top_sources: [],
    });
    const triage = h.tiles.find((t) => t.id === "triage");
    expect(triage?.status).toBe("issue");
    expect(h.ops_hints.some((x) => x.id === "untriaged_3d")).toBe(true);
  });
});
