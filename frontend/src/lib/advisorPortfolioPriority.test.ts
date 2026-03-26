import { describe, expect, it } from "vitest";

import type { AdvisorPortfolioTenantEntry } from "@/lib/api";

import {
  applyAdvisorPortfolioFilters,
  advisorPrioritySortKey,
  matchesPillarFocus,
  matchesSegmentFilter,
  priorityLabelDe,
} from "./advisorPortfolioPriority";

function row(partial: Partial<AdvisorPortfolioTenantEntry>): AdvisorPortfolioTenantEntry {
  return {
    tenant_id: "t",
    tenant_name: "T",
    eu_ai_act_readiness: 0.5,
    nis2_kritis_systems_full_coverage_ratio: 0,
    high_risk_systems_count: 0,
    open_governance_actions_count: 0,
    setup_completed_steps: 0,
    setup_total_steps: 1,
    setup_progress_ratio: 0,
    ...partial,
  };
}

describe("advisorPortfolioPriority", () => {
  it("sort key falls back to medium when missing", () => {
    expect(advisorPrioritySortKey(row({}))).toBe(1);
    expect(advisorPrioritySortKey(row({ advisor_priority_sort_key: 0 }))).toBe(0);
  });

  it("priorityLabelDe covers buckets", () => {
    expect(priorityLabelDe("high")).toBe("Hoch");
    expect(priorityLabelDe("low")).toBe("Niedrig");
    expect(priorityLabelDe(undefined)).toBe("Mittel");
  });

  it("matchesPillarFocus for readiness / gai / monitoring", () => {
    const r = row({
      primary_focus_tag_de: "Readiness",
      maturity_scenario_hint: null,
    });
    expect(matchesPillarFocus(r, "readiness")).toBe(true);
    expect(matchesPillarFocus(row({ maturity_scenario_hint: "a" }), "readiness")).toBe(true);
    expect(
      matchesPillarFocus(
        row({ governance_activity_summary: { index: 40, level: "low" } }),
        "gai",
      ),
    ).toBe(true);
    expect(
      matchesPillarFocus(
        row({
          primary_focus_tag_de: "Monitoring",
          operational_monitoring_summary: { index: 20, level: "high" },
        }),
        "monitoring",
      ),
    ).toBe(true);
  });

  it("applyAdvisorPortfolioFilters respects scenario and priority bucket", () => {
    const rows = [
      row({
        tenant_id: "a",
        maturity_scenario_hint: "a",
        advisor_priority: "high",
      }),
      row({
        tenant_id: "b",
        maturity_scenario_hint: "d",
        advisor_priority: "low",
      }),
    ];
    expect(
      applyAdvisorPortfolioFilters(rows, {
        pillar: null,
        scenario: "a",
        segment: null,
        priorityBucket: null,
      }).map((x) => x.tenant_id),
    ).toEqual(["a"]);
    expect(
      applyAdvisorPortfolioFilters(rows, {
        pillar: null,
        scenario: null,
        segment: null,
        priorityBucket: "low",
      }).map((x) => x.tenant_id),
    ).toEqual(["b"]);
  });

  it("matchesSegmentFilter aufbau_monitoring vs optimierung", () => {
    const highA = row({ advisor_priority: "high", maturity_scenario_hint: null });
    const scenarioA = row({ advisor_priority: "medium", maturity_scenario_hint: "a" });
    const lowD = row({ advisor_priority: "low", maturity_scenario_hint: "d" });
    expect(matchesSegmentFilter(highA, "aufbau_monitoring")).toBe(true);
    expect(matchesSegmentFilter(scenarioA, "aufbau_monitoring")).toBe(true);
    expect(matchesSegmentFilter(lowD, "optimierung")).toBe(true);
    expect(matchesSegmentFilter(highA, "optimierung")).toBe(false);
  });
});
