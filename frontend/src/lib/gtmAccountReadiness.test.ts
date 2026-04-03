import { describe, expect, it } from "vitest";

import { classifyMappedTenantReadiness, type GtmGovernanceSignalsInput } from "@/lib/gtmAccountReadiness";

function base(over: Partial<GtmGovernanceSignalsInput> = {}): GtmGovernanceSignalsInput {
  return {
    ai_systems_count: 0,
    progress_steps: [],
    active_frameworks: [],
    fetch_ok: true,
    ...over,
  };
}

describe("classifyMappedTenantReadiness", () => {
  it("returns early_pilot when API not ok", () => {
    expect(classifyMappedTenantReadiness(base({ fetch_ok: false }))).toBe("early_pilot");
  });

  it("advanced when board step, 2+ systems, 2+ frameworks", () => {
    expect(
      classifyMappedTenantReadiness(
        base({
          ai_systems_count: 2,
          progress_steps: [3, 4, 6],
          active_frameworks: ["eu_ai_act", "iso_42001"],
        }),
      ),
    ).toBe("advanced_governance");
  });

  it("baseline when step 6 alone", () => {
    expect(
      classifyMappedTenantReadiness(
        base({
          progress_steps: [6],
          ai_systems_count: 0,
        }),
      ),
    ).toBe("baseline_governance");
  });

  it("baseline when inventory + KPI steps", () => {
    expect(
      classifyMappedTenantReadiness(
        base({
          progress_steps: [3, 4],
          ai_systems_count: 1,
        }),
      ),
    ).toBe("baseline_governance");
  });

  it("early_pilot when only systems, no baseline rule", () => {
    expect(
      classifyMappedTenantReadiness(
        base({
          ai_systems_count: 1,
          progress_steps: [3],
        }),
      ),
    ).toBe("early_pilot");
  });
});
